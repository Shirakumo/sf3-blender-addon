import bpy
import os
import binascii
from bpy.types import Operator
from bpy_extras.io_utils import ExportHelper
from .sf3.sf3_model import Sf3Model
from .sf3.sf3_archive import Sf3Archive
from .sf3.sf3_image import Sf3Image
from .sf3.kaitaistruct import KaitaiStream

def wrap_string(str, instance):
    instance.value = str
    instance.len = len(str.encode('utf-8'))+1
    return instance

def node_input(node, input):
    if 0 < len(node.inputs[input].links):
        return node.inputs[input].links[0].from_node
    return None

def save_image(file, src_image, config={}, storage=None):
    if config.image_type == 'None':
        return file
    if config.image_type == 'SF3':
        return export_image(file, src_image, config, storage)
    image = src_image.copy()
    image.update()
    image.scale(*src_image.size)
    if config.image_type != 'AUTO':
        image.file_format = config.image_type
    image.filepath_raw = file
    if file_format in ["JPEG", "WEBP"]:
        image.save(quality=config['image_quality'])
    else:
        image.save()
    bpy.data.images.remove(image, do_unlink=True)

def zup2yup(x):
    for i in range(0, len(x), 3):
        y = x[i+1]
        x[i+1] = x[i+2]
        x[i+2] = -y
    return x

def flatten_vertex_attributes(vertex_attributes, vert_count):
    vertices = []
    # First attribute is always positions, so triplets
    for i in range(vert_count):
        for a in vertex_attributes:
            stride = len(a)//vert_count
            for v in range(i*stride, (i+1)*stride):
                vertices.append(a[v])
    return vertices

def deduplicate_vertices(vertices, stride):
    print(stride)
    set = {}
    out_indices = []
    out_vertices = []
    for i in range(0, len(vertices), stride):
        vertex = tuple(vertices[i:i+stride])
        index = set.get(vertex)
        if index is None:
            index = len(set)
            set[vertex] = index
            out_vertices.extend(vertex)
        out_indices.append(index)
    return (out_vertices, out_indices)

def export_archive(file, files, config={}, storage=None):
    print("Exporting archive to "+file)
    archive = Sf3Archive()
    archive.magic = b"\x81\x53\x46\x33\x00\xE0\xD0\x0D\x0A\x0A"
    archive.format_id = b"\x01"
    archive.checksum = 0
    archive.null_terminator = b"\x00"
    ar = Sf3Archive.Archive(_parent=archive, _root=archive)
    ar.entry_count = len(files)
    ar.meta_size = 0
    ar.meta_entry_offsets = []
    ar.entries = []
    ar.file_offsets = []
    ar.file_payloads = []
    file_sizes = 0
    for i in range(0,len(files)):
        buf = open(files[i].file,'rb').read()
        entry = Sf3Archive.MetaEntry(_parent=ar, _root=archive)
        entry.checksum = binascii.crc32(buf) & 0xFFFFFFFF
        entry.mod_time = os.path.getmtime(files[i].file)
        entry.mime = wrap_string(files[i].mime, Sf3Archive.String1(_parent=entry, _root=archive))
        entry.path = wrap_string(files[i].path, Sf3Archive.String2(_parent=entry, _root=archive))
        payload = Sf3Archive.File(_parent=ar, _root=archive)
        payload.length = len(buf)
        payload.payload = buf
        entry_size = 8+4+entry.mime.len+1+entry.path.len+2
        ar.entries.append(entry)
        ar.meta_entry_offsets.append(ar.meta_size)
        ar.meta_size += entry_size
        ar.file_offsets.append(file_sizes)
        ar.file_payloads.append(payload)
        file_sizes += len(buf)+8

    archive._check()
    f = open(file, 'wb')
    with KaitaiStream(f) as _io:
        archive._write(_io)
    return file

def export_image(file, img, config={}, storage=None):
    print("Exporting image to "+file)
    image = Sf3Image()
    image.magic = b"\x81\x53\x46\x33\x00\xE0\xD0\x0D\x0A\x0A"
    image.format_id = b"\x03"
    image.checksum = 0
    image.null_terminator = b"\x00"
    i = image.image = Sf3Image.Image(_parent=image, _root=image)
    i.width = img.size[0]
    i.heigh = img.size[1]
    i.depth = 1
    i.format = Sf3Image.Formats.uint8

    if(img.depth == 8):
        i.channel_format = Sf3Image.Layouts.v
    elif(img.depth == 16):
        i.channel_format = Sf3Image.Layouts.va
    elif(img.channels == 24):
        i.channel_format = Sf3Image.Layouts.rgb
    elif(img.channels == 32):
        i.channel_format = Sf3Image.Layouts.rgba
    elif(img.channels == 64):
        i.channel_format = Sf3Image.Layouts.va
        i.format = Sf3Image.Formats.float32
    elif(img.channels == 96):
        i.channel_format = Sf3Image.Layouts.rgb
        i.format = Sf3Image.Formats.float32
    elif(img.channels == 128):
        i.channel_format = Sf3Image.Layouts.rgba
        i.format = Sf3Image.Formats.float32

    src = img.pixels
    dst = []
    conv = lambda x: x
    if image.format & 32 == 32:
        dst = [0.0] * (i.width * i.height * i.depth)
    else:
        dst = [0] * (i.width * i.height * i.depth)
        conv = lambda x: round(x*255)

    def from_1(i):
        i = i*1
        r = conv(src[i+0])
        return (r,r,r,1.0)
    def from_2(i):
        i = i*2
        r = conv(src[i+0])
        a = conv(src[i+1])
        return (r,r,r,a)
    def from_3(i):
        i = i*3
        r = conv(src[i+0])
        g = conv(src[i+1])
        b = conv(src[i+2])
        return (r,g,b,1.0)
    def from_4(i):
        i = i*4
        r = conv(src[i+0])
        g = conv(src[i+1])
        b = conv(src[i+2])
        a = conv(src[i+3])
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
    if img.channel_format & 0xF == 2:
        dst_enc = to_2
    if img.channel_format & 0xF == 3:
        dst_enc = to_3
    if img.channel_format & 0xF== 4:
        dst_enc = to_4
    src_dec = from_1
    if img.channels == 2:
        src_dec = from_2
    if img.channels == 3:
        src_dec = from_3
    if img.channels == 4:
        src_dec = from_4

    for i in range(0, i.width * i.height):
        (r,g,b,a) = src_dec(i)
        dst_enc(i,r,g,b,a)

    i.samples = dst
    image._check()
    f = open(file, 'wb')
    with KaitaiStream(f) as _io:
        image._write(_io)
    return file

def export_model(file, obj, config={}, storage=None):
    print("Exporting model to "+file)
    dir = os.path.dirname(file)
    faces = []
    vertex_type = 1
    material_type = 0
    mesh = obj.data
    mesh.calc_loop_triangles()
    vertex_attributes = []
    textures = []

    ## We first duplicate every vertex for every face.
    indices = [0] * (len(mesh.loop_triangles)*3)
    mesh.loop_triangles.foreach_get('loops', indices)
    vertices = [0.0] * (len(indices)*3)
    for i in indices:
        vertex = mesh.vertices[mesh.loops[i].vertex_index].co
        faces.append(len(vertices)//3)
        vertices.append(vertex[0])
        vertices.append(vertex[1])
        vertices.append(vertex[2])
    vertices = zup2yup(vertices)
    vertex_attributes.append(vertices)
    stride = 3

    if 0 < len(mesh.uv_layers) and config['export_uvs']:
        vertex_type = vertex_type | 2
        uvs = [0.0] * (len(mesh.loops)*2)
        mesh.uv_layers[0].uv.foreach_get('vector', uvs)
        vertex_attributes.append(uvs)
        stride += 2
    if 0 < len(mesh.color_attributes) and config['export_colors']:
        vertex_type = vertex_type | 4
        colors = [0.0] * (len(mesh.loops)*3)
        mesh.color_attributes[0].data.foreach_get('color', colors)
        vertex_attributes.append(colors)
        stride += 3
    if config['export_normals']:
        vertex_type = vertex_type | 8
        normals = [0.0] * (len(mesh.loops)*3)
        mesh.corner_normals.foreach_get('vector', normals)
        vertex_attributes.append(zup2yup(normals))
        stride += 3
    if config['export_tangents']:
        vertex_type = vertex_type | 16
        tangents = [0.0] * (len(mesh.loops)*3)
        mesh.loops.foreach_get('tangent', tangents)
        vertex_attributes.append(zup2yup(tangents))
        stride += 3

    vertices = flatten_vertex_attributes(vertex_attributes, len(indices))
    (vertices, indices) = deduplicate_vertices(vertices, stride)

    if 0 < len(obj.data.materials):
        def try_add(tex_node, bit):
            if tex_node is not None:
                tex = save_image(os.path.join(dir, name), tex_node.image, config, storage)
                if tex:
                    material_type = material_type | bit
                    textures.append(tex)
        
        nodes = obj.data.materials[0].node_tree.nodes
        bsdf = nodes.get("Principled BSDF")
        outp = nodes.get("Material Output")
        
        try_add(node_input(bsdf, 'Base Color'), 'albedo', 1)
        try_add(node_input(bsdf, 'Normal'), 'normal', 2)
        # Decode the node mess to extract MRO or separeted textures.
        metallic = node_input(bsdf, 'Metallic')
        roughness = node_input(bsdf, 'Roughness')
        occlusion = node_input(outp, 'Surface')
        if isinstance(occlusion, bpy.types.ShaderNodeMixShader):
            ## The occlusion is encoded as a mix on the shader output
            occlusion = node_input(occlusion, 0)
        if (isinstance(metallic, bpy.types.ShaderNodeSeparateColor) and
            metallic == roughness and metallic == occlusion):
            try_add(metallic, 'metallic', 4)
        else:
            if isinstance(metallic, bpy.types.ShaderNodeTexImage):
                try_add(metallic, 'metalness', 8)
            if isinstance(roughness, bpy.types.ShaderNodeTexImage):
                try_add(roughness, 'roughness', 16)
            if isinstance(occlusion, bpy.types.ShaderNodeTexImage):
                try_add(occlusion, 'occlusion', 32)
        # If we don't have any PBR textures yet, add the specular texture.
        if 0 == material_type & 0b111100:
            try_add(node_input(bsdf, 'Specular Tint'), 'specular', 64)
        try_add(node_input(bsdf, 'Emission Color'), 'emissive', 128)
    
    # Kaitai serialization is really.... really.... annoyingly cumbersome
    model = Sf3Model()
    model.magic = b"\x81\x53\x46\x33\x00\xE0\xD0\x0D\x0A\x0A"
    model.format_id = b"\x05"
    model.checksum = 0
    model.null_terminator = b"\x00"
    mod = model.model = Sf3Model.Model(_parent=model, _root=model)
    mod.format = Sf3Model.VertexFormat(_parent=mod, _root=model)
    mod.format.raw = vertex_type
    mod.material_type = Sf3Model.MaterialType(_parent=mod, _root=model)
    mod.material_type.raw = material_type
    mod.material_size = sum([str.len+2 for str in textures])
    mod.material = Sf3Model.Material()
    # Re-wrap textures in String2
    for i in range(0, len(textures)):
        textures[i] = wrap_string(textures[i], Sf3Model.String2(_parent=mod.material, _root=model))
    mod.material.textures = textures
    mod.vertex_data = Sf3Model.VertexData(_parent=mod, _root=model)
    mod.vertex_data.face_count = len(faces)
    mod.vertex_data.faces = faces
    mod.vertex_data.vertex_count = len(vertices)
    mod.vertex_data.vertices = vertices
    model._check()
    f = open(file, 'wb')
    with KaitaiStream(f) as _io:
        model._write(_io)
    return file

class ExportSF3(Operator, ExportHelper):
    bl_idname = 'export_scene.sf3'
    bl_label = 'Export SF3'
    
    filename_ext = '.sf3'
    filter_glob: bpy.props.StringProperty(default='*.sf3', options={'HIDDEN'})

    image_type: bpy.props.EnumProperty(
        name='Images',
        items=(('AUTO', 'Automatic', 'Save images in their original format, or PNG'),
               ('SF3', 'SF3 Format', 'Save images as lossless, uncompressed SF3 images'),
               ('PNG', 'PNG Format', 'Save images as lossless PNGs'),
               ('BMP', 'BitMaP Format', 'Save images as lossless, uncompressed BMPs'),
               ('TGA', 'Targa Format', 'Save images as lossless, uncompressed TGAs'),
               ('JPEG', 'JPEG Format', 'Same images as lossy JPEGs'),
               ('WEBP', 'WebP Format', 'Save images as lossy WebPs'),
               ('NONE', 'None', 'Don\'t export images')),
        description='Output format for images.',
        default='AUTO',
    )
    image_quality: bpy.props.IntProperty(
        name='Image Quality',
        description='The quality of the image for compressed formats',
        default=80, min=1, max=100,
    )
    export_archive: bpy.props.BoolProperty(
        name='Export as Archive',
        description='Whether to export as a bundled archive. If false, exports as one or more SF3 files and image files.',
        default=True,
    )
    export_uvs: bpy.props.BoolProperty(
        name='Export UVs',
        description='Whether to export UV maps (if existing)',
        default=True,
    )
    export_colors: bpy.props.BoolProperty(
        name='Export Colors',
        description='Whether to color attributes (if existing)',
        default=True,
    )
    export_normals: bpy.props.BoolProperty(
        name='Export Normals',
        description='Whether to export normal vectors',
        default=True,
    )
    export_tangents: bpy.props.BoolProperty(
        name='Export Tangents',
        description='Whether to export tangent vectors',
        default=False,
    )

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        body.prop(self, 'export_archive')
        header, body = layout.panel('SF3_export_data', default_closed=False)
        header.label(text='Data')
        if body:
            body.prop(self, 'export_uvs')
            body.prop(self, 'export_normals')
            body.prop(self, 'export_tangents')
            body.prop(self, 'export_colors')
        header, body = layout.panel('SF3_export_material', default_closed=False)
        header.label(text='Material')
        if body:
            body.prop(self, 'image_type')
            body.prop(self, 'image_quality')

    def invoke(self, context, event):
        return ExportHelper.invoke(self, context, event)

    def execute(self, context):
        return self.export_sf3(context)

    def export_sf3(self, context):
        config = {
            'filepath': self.filepath,
            'export_archive': self.export_archive,
            'image_type': self.image_type,
            'image_quality': self.image_quality,
            'export_uvs': self.export_uvs,
            'export_colors': self.export_colors,
            'export_normals': self.export_normals,
            'export_tangents': self.export_tangents,
        }
        return export_model(self.filepath, context.object, config)

def menu_func_export(self, context):
    self.layout.operator(ExportSF3.bl_idname, text='Simple File Format Family (.sf3)')

def register():
    bpy.utils.register_class(ExportSF3)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)

def unregister():
    bpy.utils.unregister_class(ExportSF3)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
