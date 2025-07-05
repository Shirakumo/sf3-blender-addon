import bpy
import bmesh
import os
import tempfile
import traceback
from pathlib import Path
from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper
from .sf3.sf3_model import Sf3Model
from .sf3.sf3_archive import Sf3Archive
from .sf3.sf3_image import Sf3Image
from .sf3 import kaitaistruct

def message_box(message="", title="SF3", icon='INFO'):
    def draw(self, context):
        self.layout.label(text=message)

    bpy.context.window_manager.popup_menu(draw, title=title, icon=icon)

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
    return (archive.file_payloads[i].payload,
            archive.meta_entries[i].mime.value,
            archive.meta_entries[i].path.value)

def import_file(file, config={}, source=None):
    if source is None:
        print("Importing file "+file)
        if not os.path.isfile(file):
            raise Exception("File does not exist: "+file)
        try:
            return import_archive(file, config)
        except kaitaistruct.ValidationNotEqualError:
            pass
        try:
            return import_model(file, config)
        except kaitaistruct.ValidationNotEqualError:
            pass
        try:
            return import_image(file, config)
        except kaitaistruct.ValidationNotEqualError:
            pass
        try:
            return bpy.data.images.load(file, check_existing=True)
        except Exception:
            print(traceback.format_exc())
        raise Exception("Failed to import, does not appear to be a valid file: "+file)
    elif isinstance(source, Sf3Archive.Archive):
        (octs, type, file) = archive_file(file, source)
        # We can't load images from octets, so write them to disk... yay.
        # Also this simplifies the parsing logic since everything goes
        # through files.
        with tempfile.TemporaryDirectory() as dir:
            path = os.path.join(dir,file)
            with open(path, 'w+b') as fp:
                fp.write(octs)
            return import_file(path, config)
    else:
        raise Exception("Unknown source type: "+type(source))

def import_image(file, config={}):
    image = Sf3Image.from_file(file).image
    print("Importing image "+file)

    if image.channel_format in [68, 84]:
        raise Exception("Unsupported image channel layout: "+image.channel_format)
    if image.format in [34]:
        raise Exception("Unsupported image pixel format: "+image.format)
    if 1 < image.depth:
        raise Exception("Images with depth are not supported.")

    img = bpy.data.images.new(os.path.basename(file), image.width, image.height,
                              alpha=(image.channel_format & 4 == 4 or image.channel_format & 2 == 2),
                              float_buffer=(image.format & 32 == 32))
    
    scalar = 1
    if image.format & 1 == 1:
        scalar = 127
    elif image.format & 2 == 2:
        scalar = 32767
    elif image.format & 4 == 4:
        scalar = 2147483647
    elif image.format & 8 == 8:
        scalar = 9223372036854775807
    if image.format & 16 == 16:
        scalar = (scalar+1) * 2 - 1
    elif image.format & 32 == 32:
        scalar = 1

    src = image.samples
    dst = [0.0] * (img.size[0] * img.size[0] * img.channels)

    def from_1(i):
        i = i*1
        r = src[i+0] / scalar
        return (r,r,r,1.0)
    def from_2(i):
        i = i*2
        r = src[i+0] / scalar
        a = src[i+1] / scalar
        return (r,r,r,a)
    def from_3(i):
        i = i*3
        r = src[i+0] / scalar
        g = src[i+1] / scalar
        b = src[i+2] / scalar
        return (r,g,b,1.0)
    def from_4(i):
        i = i*4
        r = src[i+0] / scalar
        g = src[i+1] / scalar
        b = src[i+2] / scalar
        a = src[i+3] / scalar
        return (r,g,b,a)

    def to_1(i,r,g,b,a):
        i = i*1
        dst[i+0] = r
    def to_2(i,r,g,b,a):
        i = i*2
        dst[i+0] = r
        dst[i+1] = a
    def to_3(i,r,g,b,a):
        i = i*3
        dst[i+0] = r
        dst[i+1] = g
        dst[i+2] = b
    def to_4(i,r,g,b,a):
        i = i*4
        dst[i+0] = r
        dst[i+1] = g
        dst[i+2] = b
        dst[i+3] = a

    dst_enc = to_1
    if img.channels == 2:
        dst_enc = to_2
    if img.channels == 3:
        dst_enc = to_3
    if img.channels == 4:
        dst_enc = to_4
    src_dec = from_1
    if image.channel_format & 0xF == 2:
        src_dec = from_2
    if image.channel_format & 0xF == 3:
        src_dec = from_3
    if image.channel_format & 0xF == 4:
        src_dec = from_4

    for i in range(0, image.width * image.height):
        (r,g,b,a) = src_dec(i)
        dst_enc(i,r,g,b,a)

    img.pixels = dst
    img.update()
    return img

def import_archive(file, config={}):
    archive = Sf3Archive.from_file(file).archive
    print("Importing archive "+file)
    models = []
    for i in range(0, len(archive.meta_entries)):
        mime = archive.meta_entries[i].mime.value
        file = archive.meta_entries[i].path.value
        print("{0}: {1} {2}".format(i, file, mime))
        if mime == "model/x.sf3":
            models.append(import_file(i, config, archive))
    return models

def import_model(file, config={}, name=None, source=None):
    dir = os.path.dirname(file)
    if name is None:
        name = Path(file).stem
    mod = Sf3Model.from_file(file).model
    print("Importing model "+file)
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
            img = None
            try:
                img = import_file(texpath, config, source)
            except Exception as e:
                print(e)
                message_box("Failed to load texture "+texpath)
                img = bpy.data.images.new(texpath, 1, 1)
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
                import_file(path, import_settings)
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

