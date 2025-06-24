import bpy
import bmesh
import os
import tempfile
import mimetypes
from pathlib import Path
from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper
from .sf3.sf3_model import Sf3Model
from .sf3.sf3_archive import Sf3Archive
from .sf3.sf3_image import Sf3Image

def path_index(path, archive):
    for i in range(0, len(archive.meta_entries)):
        if path == archive.meta_entries[i].path.value:
            return i
    return None

def archive_file(file, archive):
    i = file
    if isinstance(file, str):
        i = path_index(file, source)
    if i is None:
        raise Exception("File not found in archive: "+file)
    return (archive.file_payloads[i].value,
            archive.meta_entries[i].mime.value,
            archive.meta_entries[i].path.value)

def import_file(file, config={}, source=None):
    if source is None:
        try:
            return import_archive(file, config)
        except:
            pass
        try:
            return imort_model(file, config)
        except:
            pass
        try:
            return import_image(file, config)
        except:
            pass
        try:
            return bpy.data.images.load(file, check_existing=True)
        except:
            pass
        raise Exception("Failed to import, does not appear to be a valid file: "+file)
    elif isinstance(source, Sf3Archive.Archive):
        (octs, type, file) = archive_file(file, source)
        # We can't load images from octets, so write them to disk... yay.
        # Also this simplifies the parsing logic since everything goes
        # through files.
        ext = mimetypes.guess_extension(type)
        if type in ["image/x.sf3", "model/x.sf3", "application/x.sf3-archive"]:
            ext = ".sf3"
        elif ext is None:
            ext = ".dat"
        with tempfile.NamedTemporaryFile(prefix=os.path.basename(file), suffix=ext) as fp:
            fp.write(octs)
            fp.close()
            return import_file(fp.name, config)
    else:
        raise Exception("Unknown source type: "+type(source))

def import_image(file, config={}):
    print("Importing image "+file)
    image = Sf3Image.from_file(file).image

    if image.channel_format in [68, 84]:
        raise Exception("Unsupported image channel layout: "+image.channel_format)
    if image.format in [34]:
        raise Exception("Unsupported image pixel format: "+image.format)

    img = bpy.data.images.new(file, image.width, image.height,
                              alpha=(image.channel_format & 4 == 4 or image.channel_format & 2 == 2),
                              float_buffer=(image.format & 32 == 32))
    pixels = [0.0] * (image.width * image.height * image.channels)
    for p in range(0, image.width * image.height):
        pass
    img.pixels = pixels
    return img

def import_archive(file, config={}):
    print("Importing archive "+file)
    archive = Sf3Archive.from_file(file).archive
    models = []
    for i in range(0, len(archive.meta_entries)):
        if archive.meta_entries[i].mime.value == ["model/x.sf3"]:
            models.append(import_file(i, config, archive))
    return models

def import_model(file, config={}, name=None, source=None):
    print("Importing model "+file)
    dir = os.path.dirname(file)
    if name is None:
        name = Path(file).stem
    mod = Sf3Model.from_file(file).model
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.data.collections["Collection"].objects.link(obj)
    bpy.context.view_layer.objects.active = obj

    dat = mod.vertex_data
    stride = mod.format.vertex_stride
    vert_range = range(0, len(dat.vertices), stride)
    verts = [[dat.vertices[i+0],dat.vertices[i+2],-dat.vertices[i+1]] for i in vert_range]
    faces = [dat.faces[i:i+3] for i in range(0, len(dat.faces), 3)]
    mesh.from_pydata(verts, [], faces)

    offset = 3
    if mod.format.has_uv:
        uvs = []
        for f in faces:
            for i in f:
                uvs.append(dat.vertices[i*stride+offset+0])
                uvs.append(dat.vertices[i*stride+offset+1])
        layer = mesh.uv_layers.new(name='UVMap')
        layer.uv.foreach_set('vector', uvs)
        offset += 2
    if mod.format.has_color:
        colors = []
        for f in faces:
            for i in f:
                colors.append(dat.vertices[i*stride+offset+0])
                colors.append(dat.vertices[i*stride+offset+1])
                colors.append(dat.vertices[i*stride+offset+2])
        layer = mesh.color_attributes.new('Color', 'BYTE_COLOR', 'CORNER')
        layer.data.foreach_set('color', colors)
        offset += 3
    if mod.format.has_normal:
        normals = [[dat.vertices[i+offset+0],dat.vertices[i+offset+2],-dat.vertices[i+offset+1]] for i in vert_range]
        mesh.normals_split_custom_set_from_vertices(normals)
        offset += 3
    if mod.format.has_tangent:
        offset += 3

    if 0 < len(mod.material.textures):
        mat = bpy.data.materials.new(name=name)
        mat.use_nodes = True
        obj.data.materials.append(mat)
        obj.active_material_index = 0
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        outp = mat.node_tree.nodes.get("Material Output")

        offset = 0
        def load_texture(texname):
            texpath = os.path.join(dir, mod.material.textures[offset].value)
            img = import_image(texpath, config, source)
            tex = mat.node_tree.nodes.new('ShaderNodeTexImage')
            tex.image = img
            return tex
            
        if mod.material_type.has_albedo:
            tex = load_texture('albedo')
            mat.node_tree.links.new(bsdf.inputs['Base Color'], tex.outputs['Color'])
            mat.node_tree.links.new(bsdf.inputs['Alpha'], tex.outputs['Alpha'])
            offset += 1
        if mod.material_type.has_normal:
            tex = load_texture('normal')
            mat.node_tree.links.new(bsdf.inputs['Normal'], tex.outputs['Color'])
            offset += 1
        if mod.material_type.has_metallic:
            tex = load_texture('metallic')
            sep = mat.node_tree.nodes.new('ShaderNodeSeparateColor')
            mix = mat.node_tree.nodes.new('ShaderNodeMixShader')
            mat.node_tree.links.new(bsdf.inputs['Metallic'], sep.outputs['Red'])
            mat.node_tree.links.new(bsdf.inputs['Roughness'], sep.outputs['Green'])
            mat.node_tree.links.new(mix.inputs[0], sep.outputs['Blue'])
            mat.node_tree.links.new(mix.inputs[1], bsdf.outputs[0])
            mat.node_tree.links.new(mix.outputs[0], outp.inputs['Surface'])
            offset += 1
        if mod.material_type.has_metalness:
            tex = load_texture('metalness')
            mat.node_tree.links.new(bsdf.inputs['Metallic'], tex.outputs['Color'])
            offset += 1
        if mod.material_type.has_roughness:
            tex = load_texture('roughness')
            mat.node_tree.links.new(bsdf.inputs['Roughness'], tex.outputs['Color'])
            offset += 1
        if mod.material_type.has_occlusion:
            tex = load_texture('occlusion')
            mix = mat.node_tree.nodes.new('ShaderNodeMixShader')
            mat.node_tree.links.new(mix.inputs[1], tex.outputs['Color'])
            mat.node_tree.links.new(mix.inputs[2], bsdf.outputs[0])
            mat.node_tree.links.new(mix.outputs[0], outp.inputs['Surface'])
            offset += 1
        if mod.material_type.has_specular:
            tex = load_texture('specular')
            mat.node_tree.links.new(bsdf.inputs['Specular Tint'], tex.outputs['Color'])
            offset += 1
        if mod.material_type.has_emission:
            tex = load_texture('emission')
            mat.node_tree.links.new(bsdf.inputs['Emission Color'], tex.outputs['Color'])
            offset += 1
    return obj

class ImportSF3(Operator, ImportHelper):
    bl_idname = 'import_scene.sf3'
    bl_label = 'Import SF3'
    bl_options = {'REGISTER', 'UNDO'}
    
    filter_glob: bpy.props.StringProperty(default="*.sf3", options={'HIDDEN'})
    
    files: bpy.props.CollectionProperty(
        name="File Path",
        type=bpy.types.OperatorFileListElement,
    )

    def draw(self, context):
        layout = self.layout

        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

    def invoke(self, context, event):
        return ImportHelper.invoke_popup(self, context)

    def execute(self, context):
        return self.import_sf3(context)

    def import_sf3(self, context):
        import_settings = {}
        if self.files:
            ret = {'CANCELLED'}
            dirname = os.path.dirname(self.filepath)
            for file in self.files:
                path = os.path.join(dirname, file.name)
                import_model(path, import_settings)
                ret = {'FINISHED'}
            return ret
        else:
            return import_file(self.filepath, import_settings)
        return {'FINISHED'}

def menu_func_import(self, context):
    self.layout.operator(ImportSF3.bl_idname, text='Simple File Format Family (.sf3)')

def register():
    bpy.utils.register_class(ImportSF3)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)

def unregister():
    bpy.utils.unregister_class(ImportSF3)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)

