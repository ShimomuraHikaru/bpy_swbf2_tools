from . import parse_zero
import bpy
import mathutils
from bpy_extras.io_utils import ImportHelper

import os
from . import msh2_crc

MODL_NULL, \
MODL_GEODYNAMIC, \
MODL_CLOTH, \
MODL_BONE, \
MODL_GEOBONE, \
MODL_GEOSTATIC, \
MODL_GEOSHADOW = range(7)

MAT_ZERO_2_BLENDER = mathutils.Matrix(((1.0, 0.0, 0.0), # conversion matrix for just about every thing
                            (0.0, 0.0, 1.0),
                            (0.0, 1.0, 0.0))).to_4x4()


def vec3d_conv_2_bldr(vec):
    assert isinstance(vec, tuple) and len(vec) == 3, 'must be a tuple with no more or less than 3 items'
    temp_vec = mathutils.Vector(vec)
    return (temp_vec @ MAT_ZERO_2_BLENDER).to_tuple()

def convert_trans(trans):
    assert isinstance(trans, parse_zero.zeroChunk)
    mat_loc = mathutils.Matrix.Translation(trans.location)
    
    quat = mathutils.Quaternion((trans.quaternion[3], trans.quaternion[0], trans.quaternion[1], trans.quaternion[2]))

    mat_rot = quat.to_matrix().to_4x4()

    mat_scale = mathutils.Matrix((
        (trans.scale[0], 0, 0),
        (0, trans.scale[1], 0),
        (0, 0, trans.scale[2]),
    )).to_4x4()

    final_mat = mat_loc @ mat_rot @ mat_scale

    return (MAT_ZERO_2_BLENDER @ final_mat).decompose()




def load(filepath, load_objects=True, load_animations=False, clear_scene=True):
    root = parse_zero.parse(filepath)

    if(clear_scene):
        for bmsh in bpy.data.meshes:
            bpy.data.meshes.remove(bmsh, do_unlink=True)

        for bobj in bpy.data.objects:
            bpy.data.objects.remove(bobj, do_unlink=True)

        for bmat in bpy.data.materials:
            bpy.data.materials.remove(bmat, do_unlink=True)

    if(load_objects):    
        model_data = parse_zero.select_chunk_from_id('MSH2', root)
        model_index_list = []
        material_index_list = []

        for child in model_data.children:
            if(child.name == 'MATL'):
                if(child.children):
                    for mat in child.children:
                        if(mat.name == 'MATD'):
                            material_index_list.append(mat)
            if(child.name == 'MODL'):
                model_index_list.append(child)
        
        for i in range(len(material_index_list)):
            mat = material_index_list[i]
            name = parse_zero.select_chunk_from_id('NAME', mat).data
            data = parse_zero.select_chunk_from_id('DATA', mat)
            atrb = parse_zero.select_chunk_from_id('ATRB', mat)
            
            tex1 = parse_zero.select_chunk_from_id('TX0D', mat)
            tex2 = parse_zero.select_chunk_from_id('TX1D', mat)
            tex3 = parse_zero.select_chunk_from_id('TX2D', mat)
            tex4 = parse_zero.select_chunk_from_id('TX3D', mat)


            bmat = bpy.data.materials.new(name=name)
            bmat.ze_material.index = i
            bmat.ze_material.diffuse = data.diffuse
            bmat.ze_material.specular = data.specular_color
            bmat.ze_material.ambient = data.ambient
            bmat.ze_material.specular_sharpness = data.specular_strength
            bmat.ze_material['flags'] = atrb.flags
            bmat.ze_material['render_type'] = atrb.render_type
            bmat.ze_material.data1 = atrb.data0
            bmat.ze_material.data2 = atrb.data1

            bmat.use_nodes = True
            
            tex_path1, tex_path2, tex_path3, tex_path4 = ['','','','']

            if(tex1):    
                tex_path1 = '{0}/{1}'.format(os.path.dirname(filepath), tex1.data)
            if(tex2):
                tex_path2 = '{0}/{1}'.format(os.path.dirname(filepath), tex2.data)
            if(tex3):
                tex_path3 = '{0}/{1}'.format(os.path.dirname(filepath), tex3.data)
            if(tex4):
                tex_path4 = '{0}/{1}'.format(os.path.dirname(filepath), tex4.data)
                
            if(os.path.exists(tex_path1)):
                img = bpy.data.images.load(tex_path1)
                bmat.ze_material.texture1 = img
                tree = bmat.node_tree
                shad_node = tree.nodes[0]
                tex_node = tree.nodes.new('ShaderNodeTexImage')
                tex_node.image = img
                tree.links.new(shad_node.inputs[0], tex_node.outputs[0])
            if(os.path.exists(tex_path2)):
                img = bpy.data.images.load(tex_path2)
                bmat.ze_material.texture2 = img
            if(os.path.exists(tex_path3)):
                img = bpy.data.images.load(tex_path3)
                bmat.ze_material.texture3 = img
            if(os.path.exists(tex_path4)):
                img = bpy.data.images.load(tex_path4)
                bmat.ze_material.texture4 = img
            
        
        for model in model_index_list:
            m_name = parse_zero.select_chunk_from_id('NAME', model).data
            m_type = parse_zero.select_chunk_from_id('MTYP', model).model_type
            m_index = parse_zero.select_chunk_from_id('MNDX', model).model_index
            m_flag = parse_zero.select_chunk_from_id('FLGS', model)
            m_collision = parse_zero.select_chunk_from_id('SWCI', model)
            if(m_flag):
                m_flag = m_flag.flags
            else:
                m_flag = 0

            obj = None
            #print(m_name)

            if(m_type == MODL_NULL):
                obj = create_null_object(model)
            elif(m_type == MODL_GEOSTATIC):
                obj = create_static_object(model)
            elif(m_type == MODL_GEODYNAMIC):
                obj = create_geodynamic_object(model)
                set_weights(obj, model, model_index_list)
            elif(m_type == MODL_BONE):
                obj = create_bone(model)
            elif(m_type == MODL_CLOTH):
                obj = create_cloth_object(model)
                set_weights_cloth(obj, model, model_index_list)
            elif(m_type == MODL_GEOBONE):
                obj = create_geobone_object(model)
            elif(m_type == MODL_GEOSHADOW):
                obj = create_shadow_object(model)

            obj.ze_object.object_index = m_index
            obj.ze_object['object_type'] = m_type
            obj.ze_object.hidden = m_flag

            if(m_collision):
                obj.ze_object.collision = True
                obj.ze_object['collision_type'] = m_collision.coll_type
                obj.ze_object.collision_x = m_collision.x
                obj.ze_object.collision_y = m_collision.y
                obj.ze_object.collision_z = m_collision.z
                
            skel = parse_zero.select_chunk_from_id('SKL2', root)
            blen = parse_zero.select_chunk_from_id('BLN2', root)

            if(obj):
                bpy.context.scene.collection.objects.link(obj)

        print(bpy.data.objects.keys())
        for model in model_index_list:
            coll = parse_zero.select_chunk_from_id('COLL', model)
            if(coll):
                cl_name = parse_zero.select_chunk_from_id('NAME', model).data
                cloth_object = bpy.data.objects[cl_name]
                for i in range(len(coll.collisions)):
                    c = cloth_object.ze_cloth_collision_objects.add()
                    c.ob = bpy.data.objects[coll.collisions[i].ob_name]
                    c['ob_type'] = coll.collisions[i].col_type
                    c.x = coll.collisions[i].x
                    c.y = coll.collisions[i].y
                    c.z = coll.collisions[i].z
        
        for obj in bpy.data.objects:
            if(skel):
                for bone in skel.bones:
                    if(msh2_crc.crc(obj.name) == bone.crc):
                        obj.ze_object.chain_object = True
                        obj.ze_object.constraint = bone.constrain
                        break
            if(blen):
                for wgt in blen.values:
                    if(msh2_crc.crc(obj.name) == wgt.crc):
                        obj.ze_object.blend_factor = wgt.value
                        break

        create_armature_from_model_list(model_index_list)

    if(load_animations):
        load_animation(root)

def create_null_object(model):
    name = parse_zero.select_chunk_from_id('NAME', model).data
    new_obj = bpy.data.objects.new(name=name, object_data=None)
    new_obj.empty_display_size = 0.05
    #new_obj.show_name = True

    parent = parse_zero.select_chunk_from_id('PRNT', model)
    trans = parse_zero.select_chunk_from_id('TRAN', model)
    #loc, rot, scale = trans.location, mathutils.Quaternion((trans.quaternion[3],
    #trans.quaternion[0], trans.quaternion[1], trans.quaternion[2])), trans.scale
    loc, rot, scale = trans.location, mathutils.Quaternion((trans.quaternion[3],
    trans.quaternion[0], -trans.quaternion[2], trans.quaternion[1])), trans.scale

    x, y, z = loc
    loc = x, -z, y
    x, y, z = scale
    scale = x, z, y

    ##print(loc, rot, scale, sep='\n', end='\n\n')

    if(parent):
        new_obj.parent = bpy.data.objects[parent.data]
        #loc, rot, scale = convert_trans_to_world(trans, new_obj.parent.matrix_world)

    new_obj.rotation_mode = 'QUATERNION'
    new_obj.location = loc
    new_obj.rotation_quaternion = rot
    new_obj.scale = scale

    ##print(trans.scale, trans.quaternion, trans.location)
    return new_obj

def create_geodynamic_object(model):
    new_mesh = create_mesh(model)
    name = parse_zero.select_chunk_from_id('NAME', model).data
    new_obj = bpy.data.objects.new(name, new_mesh)

    parent = parse_zero.select_chunk_from_id('PRNT', model)
    trans = parse_zero.select_chunk_from_id('TRAN', model)
    #loc, rot, scale = trans.location, mathutils.Quaternion((trans.quaternion[3],
    #trans.quaternion[0], trans.quaternion[1], trans.quaternion[2])), trans.scale

    loc, rot, scale = trans.location, mathutils.Quaternion((trans.quaternion[3],
    trans.quaternion[0], -trans.quaternion[2], trans.quaternion[1])), trans.scale

    x, y, z = loc
    loc = x, -z, y
    x, y, z = scale
    scale = x, z, y

    ##print(loc, rot, scale, sep='\n', end='\n\n')

    if(parent):
        new_obj.parent = bpy.data.objects[parent.data]
        #loc, rot, scale = convert_trans_to_world(trans, new_obj.parent.matrix_world)

    new_obj.rotation_mode = 'QUATERNION'
    new_obj.location = loc
    new_obj.rotation_quaternion = rot
    new_obj.scale = scale

    return new_obj

def create_static_object(model):
    new_mesh = create_mesh(model)
    name = parse_zero.select_chunk_from_id('NAME', model).data
    new_obj = bpy.data.objects.new(name, new_mesh)

    parent = parse_zero.select_chunk_from_id('PRNT', model)
    trans = parse_zero.select_chunk_from_id('TRAN', model)
    #loc, rot, scale = trans.location, mathutils.Quaternion((trans.quaternion[3],
    #trans.quaternion[0], trans.quaternion[1], trans.quaternion[2])), trans.scale

    loc, rot, scale = trans.location, mathutils.Quaternion((trans.quaternion[3],
    trans.quaternion[0], -trans.quaternion[2], trans.quaternion[1])), trans.scale

    x, y, z = loc
    loc = x, -z, y
    x, y, z = scale
    scale = x, z, y

    ##print(loc, rot, scale, sep='\n', end='\n\n')

    if(parent):
        new_obj.parent = bpy.data.objects[parent.data]
        #loc, rot, scale = convert_trans_to_world(trans, new_obj.parent.matrix_world)

    new_obj.rotation_mode = 'QUATERNION'
    new_obj.location = loc
    new_obj.rotation_quaternion = rot
    new_obj.scale = scale

    return new_obj

def create_bone(model):
    new_obj = None
    geom = parse_zero.select_chunk_from_id('GEOM', model)
    if(geom):
        new_mesh = create_mesh(model)
        name = parse_zero.select_chunk_from_id('NAME', model).data
        new_obj = bpy.data.objects.new(name, new_mesh)

        parent = parse_zero.select_chunk_from_id('PRNT', model)
        trans = parse_zero.select_chunk_from_id('TRAN', model)
        #loc, rot, scale = trans.location, mathutils.Quaternion((trans.quaternion[3],
        #trans.quaternion[0], trans.quaternion[1], trans.quaternion[2])), trans.scale
        loc, rot, scale = trans.location, mathutils.Quaternion((trans.quaternion[3],
        trans.quaternion[0], -trans.quaternion[2], trans.quaternion[1])), trans.scale

        x, y, z = loc
        loc = x, -z, y
        x, y, z = scale
        scale = x, z, y

        ##print(loc, rot, scale, sep='\n', end='\n\n')

        if(parent):
            new_obj.parent = bpy.data.objects[parent.data]
            #loc, rot, scale = convert_trans_to_world(trans, new_obj.parent.matrix_world)

        new_obj.rotation_mode = 'QUATERNION'
        new_obj.location = loc
        new_obj.rotation_quaternion = rot
        new_obj.scale = scale

    else:
        new_obj = create_null_object(model)
        new_obj.empty_display_type = 'CUBE'
        new_obj.empty_display_size = 0.04
    
    return new_obj
"""
def create_bone(model):
    new_obj = None
    geom = parse_zero.select_chunk_from_id('GEOM', model)
    if(geom):
        new_mesh = create_mesh(model)
        name = parse_zero.select_chunk_from_id('NAME', model).data
        new_obj = bpy.data.objects.new(name, new_mesh)

        parent = parse_zero.select_chunk_from_id('PRNT', model)
        trans = parse_zero.select_chunk_from_id('TRAN', model)
        #loc, rot, scale = trans.location, mathutils.Quaternion((trans.quaternion[3],
        #trans.quaternion[0], trans.quaternion[1], trans.quaternion[2])), trans.scale
        loc, rot, scale = trans.location, mathutils.Quaternion((trans.quaternion[3],
        trans.quaternion[0], -trans.quaternion[2], trans.quaternion[1])), trans.scale

        x, y, z = loc
        loc = x, -z, y
        x, y, z = scale
        scale = x, z, y

        ##print(loc, rot, scale, sep='\n', end='\n\n')

        if(parent):
            new_obj.parent = bpy.data.objects[parent.data]
            #loc, rot, scale = convert_trans_to_world(trans, new_obj.parent.matrix_world)

        new_obj.rotation_mode = 'QUATERNION'
        new_obj.location = loc
        new_obj.rotation_quaternion = rot
        new_obj.scale = scale

    else:
        new_obj = create_null_object(model)
        new_obj.empty_display_type = 'CUBE'
        new_obj.empty_display_size = 0.04
    
    return new_obj
    """

def create_cloth_object(model):
    new_mesh = create_cloth_mesh(model)
    name = parse_zero.select_chunk_from_id('NAME', model).data
    new_obj = bpy.data.objects.new(name, new_mesh)

    parent = parse_zero.select_chunk_from_id('PRNT', model)
    trans = parse_zero.select_chunk_from_id('TRAN', model)

    #loc, rot, scale = trans.location, mathutils.Quaternion((trans.quaternion[3],
    #trans.quaternion[0], trans.quaternion[1], trans.quaternion[2])), trans.scale
    loc, rot, scale = trans.location, mathutils.Quaternion((trans.quaternion[3],
    trans.quaternion[0], -trans.quaternion[2], trans.quaternion[1])), trans.scale

    x, y, z = loc
    loc = x, -z, y
    x, y, z = scale
    scale = x, z, y

    ##print(loc, rot, scale, sep='\n', end='\n\n')

    if(parent):
        new_obj.parent = bpy.data.objects[parent.data]
        #loc, rot, scale = convert_trans_to_world(trans, new_obj.parent.matrix_world)

    new_obj.rotation_mode = 'QUATERNION'
    new_obj.location = loc
    new_obj.rotation_quaternion = rot
    new_obj.scale = scale

    fdx = parse_zero.select_chunk_from_id('FIDX', model)
    if(fdx):
        for i in range(len(fdx.fixed_points)):
            point = new_obj.ze_cloth_fixed_points.add()
            point.value = fdx.fixed_points[i]

    stretch = parse_zero.select_chunk_from_id('SPRS', model)
    if(stretch):
        for i in range(len(stretch.stretch_constraints)):
            edge = new_obj.ze_cloth_stretch_constraints.add()
            edge.value = stretch.stretch_constraints[i]

    cross = parse_zero.select_chunk_from_id('CPRS', model)
    if(cross):
        for i in range(len(cross.cross_constraints)):
            edge = new_obj.ze_cloth_cross_constraints.add()
            edge.value = cross.cross_constraints[i]


    bend = parse_zero.select_chunk_from_id('BPRS', model)
    if(bend):
        for i in range(len(bend.bend_constraints)):
            edge = new_obj.ze_cloth_bend_constraints.add()
            edge.value = bend.bend_constraints[i]
    """
    coll = parse_zero.select_chunk_from_id('COLL', model)
    if(coll):
        for i in range(len(coll.collisions)):
            c = new_obj.ze_cloth_collision_objects.add()
            c.ob = bpy.data.objects[coll.collisions[i].ob_name]
            c['ob_type'] = coll.collisions[i].col_type
            c.x = coll.collisions[i].x
            c.y = coll.collisions[i].y
            c.z = coll.collisions[i].z
    """
    return new_obj

def create_geobone_object(model):
    new_mesh = create_mesh(model)
    name = parse_zero.select_chunk_from_id('NAME', model).data
    new_obj = bpy.data.objects.new(name, new_mesh)

    parent = parse_zero.select_chunk_from_id('PRNT', model)
    trans = parse_zero.select_chunk_from_id('TRAN', model)

    #loc, rot, scale = trans.location, mathutils.Quaternion((trans.quaternion[3],
    #trans.quaternion[0], trans.quaternion[1], trans.quaternion[2])), trans.scale
    loc, rot, scale = trans.location, mathutils.Quaternion((trans.quaternion[3],
    trans.quaternion[0], -trans.quaternion[2], trans.quaternion[1])), trans.scale

    x, y, z = loc
    loc = x, -z, y
    x, y, z = scale
    scale = x, z, y

    ##print(loc, rot, scale, sep='\n', end='\n\n')

    if(parent):
        new_obj.parent = bpy.data.objects[parent.data]
        #loc, rot, scale = convert_trans_to_world(trans, new_obj.parent.matrix_world)

    new_obj.rotation_mode = 'QUATERNION'
    new_obj.location = loc
    new_obj.rotation_quaternion = rot
    new_obj.scale = scale

    return new_obj

def create_shadow_object(model):
    new_mesh = create_shadow_mesh(model)
    name = parse_zero.select_chunk_from_id('NAME', model).data
    new_obj = bpy.data.objects.new(name, new_mesh)

    parent = parse_zero.select_chunk_from_id('PRNT', model)
    trans = parse_zero.select_chunk_from_id('TRAN', model)
    #loc, rot, scale = trans.location, mathutils.Quaternion((trans.quaternion[3],
    #trans.quaternion[0], trans.quaternion[1], trans.quaternion[2])), trans.scale
    loc, rot, scale = trans.location, mathutils.Quaternion((trans.quaternion[3],
    trans.quaternion[0], -trans.quaternion[2], trans.quaternion[1])), trans.scale

    x, y, z = loc
    loc = x, -z, y
    x, y, z = scale
    scale = x, z, y

    ##print(loc, rot, scale, sep='\n', end='\n\n')

    if(parent):
        new_obj.parent = bpy.data.objects[parent.data]
        #loc, rot, scale = convert_trans_to_world(trans, new_obj.parent.matrix_world)

    new_obj.rotation_mode = 'QUATERNION'
    new_obj.location = loc
    new_obj.rotation_quaternion = rot
    new_obj.scale = scale

    return new_obj

def create_mesh(model):

    material_index_list = []
    for child in model.parent.children:
        if(child.name == 'MATL'):
            for mat in child.children:
                if(mat.name == 'MATD'):
                    material_index_list.append(mat)
    
    name = parse_zero.select_chunk_from_id('NAME', model).data
    new_mesh = bpy.data.meshes.new(name)

    vertex_buffer = []
    triangle_buffer = []
    #uv_tri_buffer = []
    uv_buffer = None
    triangle_index_offset = 0

    vert_offsets = []
    tri_offsets = []

    mat_segm_list = []

    geometry_data = parse_zero.select_chunk_from_id('GEOM', model)
    if(geometry_data):
        for child in geometry_data.children:
            if(child.name == 'SEGM'):
                vert_seg = parse_zero.select_chunk_from_id('POSL', child).verts
                convert_vert = [(x,-z, y) for x, y, z in vert_seg]

                mati = parse_zero.select_chunk_from_id('MATI', child).material_index
                mat_segm_list.append(mati)
                print(mati, name)

                off = triangle_index_offset
                tri_seg = parse_zero.select_chunk_from_id('NDXT', child).tris
                convert_tri = [ (t1+off, t2+off, t3+off) for t1, t2, t3 in tri_seg]
                triangle_index_offset += len(vert_seg)

                uv_seg = parse_zero.select_chunk_from_id('UV0L', child)
                if(uv_seg):
                    if(uv_buffer):
                        uv_buffer.extend(uv_seg.uvs)
                    else:
                        uv_buffer = []
                        uv_buffer.extend(uv_seg.uvs)

                
                #vertex_buffer.extend(vert_seg)
                #triangle_buffer.extend(tri_seg)
                vertex_buffer.extend(convert_vert)
                triangle_buffer.extend(convert_tri)

                vert_offsets.append(len(vertex_buffer))
                tri_offsets.append(len(triangle_buffer))
                #uv_tri_buffer.extend(tri_seg)

        new_mesh.from_pydata(vertex_buffer, [], triangle_buffer)

        if(uv_buffer):
            uv_map = new_mesh.uv_layers.new(name='UV_MAP')
            for face in new_mesh.polygons:
                for vert_idx, loop_idx in zip(face.vertices, face.loop_indices):
                    #print('loop \t uv')
                    #print(loop_idx, vert_idx)
                    #print(len(uv_map.data), len(uv_buffer))
                    uv_map.data[loop_idx].uv = uv_buffer[vert_idx]
                    

        used_set = set()
        for i in mat_segm_list:
            if(not i in used_set):
                name = parse_zero.select_chunk_from_id('NAME', material_index_list[i]).data
                new_mesh.materials.append(bpy.data.materials[name])
                used_set.add(i)

        index_start = 0
        segm_index = 0
        for offset in tri_offsets:
            for i in range(index_start, offset):
                new_mesh.polygons[i].material_index = get_mesh_material_index(new_mesh, mat_segm_list[segm_index])
                pass
            segm_index += 1
            index_start = offset


    return new_mesh

def create_cloth_mesh(model):

    name = parse_zero.select_chunk_from_id('NAME', model).data
    new_mesh = bpy.data.meshes.new(name)

    vertex_buffer = []
    triangle_buffer = []
    #uv_tri_buffer = []
    uv_buffer = None
    triangle_index_offset = 0

    vert_offsets = []
    tri_offsets = []

    mat_segm_list = []

    geometry_data = parse_zero.select_chunk_from_id('CLTH', model)
    if(geometry_data):
        vert_seg = parse_zero.select_chunk_from_id('CPOS', geometry_data).cloth_verts
        convert_vert = [(x,-z, y) for x, y, z in vert_seg]

        off = triangle_index_offset
        tri_seg = parse_zero.select_chunk_from_id('CMSH', geometry_data).cloth_tris
        convert_tri = [ (t1+off, t2+off, t3+off) for t1, t2, t3 in tri_seg]
        triangle_index_offset += len(vert_seg)

        uv_seg = parse_zero.select_chunk_from_id('CUV0', geometry_data)
        if(uv_seg):
            if(uv_buffer):
                uv_buffer.extend(uv_seg.cloth_uvs)
            else:
                uv_buffer = []
                uv_buffer.extend(uv_seg.cloth_uvs)

            
        #vertex_buffer.extend(vert_seg)
        #triangle_buffer.extend(tri_seg)
        vertex_buffer.extend(convert_vert)
        triangle_buffer.extend(convert_tri)

        vert_offsets.append(len(vertex_buffer))
        tri_offsets.append(len(triangle_buffer))
        #uv_tri_buffer.extend(tri_seg)

    new_mesh.from_pydata(vertex_buffer, [], triangle_buffer)

    if(uv_buffer):
        uv_map = new_mesh.uv_layers.new(name='UV_MAP')
        for face in new_mesh.polygons:
            for vert_idx, loop_idx in zip(face.vertices, face.loop_indices):
                uv_map.data[loop_idx].uv = uv_buffer[vert_idx]

    return new_mesh

def create_shadow_mesh(model):
    name = parse_zero.select_chunk_from_id('NAME', model).data
    new_mesh = bpy.data.meshes.new(name)
    shadow = parse_zero.select_chunk_from_id('SHDW', model)
    converted_vertex_buffer = [(x, -z, y) for (x, y, z) in shadow.verts]

    face_loops = []
    used_indices = set()
    start = 0
    index = start
    face = []
    for r in range(len(shadow.edges)):
        ej = shadow.edges

        if(index == start):
            if(len(face) > 2):
                face_loops.append(face)
            start = 0
            face = []
            while(True):
                if start in used_indices:
                    start += 1
                    index = start
                else:
                    break
        
        face.append(ej[index][0])
        index = ej[index][1]
        used_indices.add(index)
    
    print(face_loops)
    new_mesh.from_pydata(converted_vertex_buffer, [], face_loops)
    new_mesh.update()

    return new_mesh

def set_weights(obj, model_chunk, model_chunk_list):
    envelope_index_list = parse_zero.select_chunk_from_id('ENVL', model_chunk).envelopes
    envelope_string_list = []

    vertex_weights = []

    for index in envelope_index_list:
        envelope_string_list.append(parse_zero.select_chunk_from_id('NAME', model_chunk_list[index-1]).data)
        # the MNDX in each MODL chunk is lined in order starting from 1
        # because the normal index for an array starts from 0, index-1
    
    for vg_name in envelope_string_list:
        obj.vertex_groups.new(name=vg_name)

    geom = parse_zero.select_chunk_from_id('GEOM', model_chunk)
    for child in geom.children:
        if(child.name == 'SEGM'):
            vertex_weights.extend(parse_zero.select_chunk_from_id('WGHT', child).weights)

    for i in range(len(obj.data.vertices)):
        #if(vertex_weights[4*i+0][0] != 0):
        obj.vertex_groups[envelope_string_list[vertex_weights[4*i+0][0]]].add([i], vertex_weights[4*i+0][1],'ADD') 
        #if(vertex_weights[4*i+1][0] != 0):
        obj.vertex_groups[envelope_string_list[vertex_weights[4*i+1][0]]].add([i], vertex_weights[4*i+1][1],'ADD')
        #if(vertex_weights[4*i+2][0] != 0):
        obj.vertex_groups[envelope_string_list[vertex_weights[4*i+2][0]]].add([i], vertex_weights[4*i+2][1],'ADD')
        #if(vertex_weights[4*i+3][0]):
        obj.vertex_groups[envelope_string_list[vertex_weights[4*i+3][0]]].add([i], vertex_weights[4*i+3][1],'ADD')

def set_weights_cloth(obj, model_chunk, model_chunk_list):
    envelope_index_list = parse_zero.select_chunk_from_id('ENVL', model_chunk).envelopes
    envelope_string_list = []

    for index in envelope_index_list:
        envelope_string_list.append(parse_zero.select_chunk_from_id('NAME', model_chunk_list[index-1]).data)
        # the MNDX in each MODL chunk is lined in order starting from 1
        # because the normal index for an array starts from 0, index-1
    
    for vg_name in envelope_string_list:
        obj.vertex_groups.new(name=vg_name)

    fwgt = parse_zero.select_chunk_from_id('FWGT', model_chunk).weights
    
    fidx = parse_zero.select_chunk_from_id('FIDX', model_chunk).fixed_points

    for i in range(len(fidx)):
        #if(vertex_weights[4*i+0][0] != 0):
        obj.vertex_groups[fwgt[i]].add([fidx[i]], 1.0,'ADD') 

def create_armature_from_model_list(model_list):
    
    scene_object_list = bpy.data.objects

    arm = bpy.data.armatures.new(name='Zero_Proxy')
    arm_object = bpy.data.objects.new('Zero_Proxy', arm)
    bpy.context.scene.collection.objects.link(arm_object)

    #enter editmode
    bpy.context.view_layer.objects.active = arm_object
    bpy.ops.object.mode_set(mode='EDIT')

    for model in model_list:
        m_name = parse_zero.select_chunk_from_id('NAME', model).data
        m_type = parse_zero.select_chunk_from_id('MTYP', model).model_type
        if(m_type == MODL_BONE):
            arm.edit_bones.new(name=m_name).length = 0.06

    # exit editmode
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # pose mode???

    for bone in arm_object.pose.bones:
        bone.matrix = scene_object_list[bone.name].matrix_world #@ MAT_ZERO_2_BLENDER

    bpy.ops.object.mode_set(mode='POSE')
    
    bpy.ops.pose.armature_apply()

    bpy.ops.object.mode_set(mode='EDIT')

    parent = None
    for bone in arm.edit_bones:
        if(scene_object_list[bone.name].parent):
            parent = scene_object_list[bone.name].parent
            if(parent.name in arm.edit_bones.keys()):
                bone.parent = arm.edit_bones[parent.name]
            else:
                while(parent != None):
                    if(parent.name in arm.edit_bones.keys()):
                        break

                    parent = parent.parent
                if(parent != None):
                    bone.parent = arm.edit_bones[parent.name]

    bpy.ops.object.mode_set(mode='OBJECT')

    # exit???

def load_animation(file_root):

    scene_info = parse_zero.select_chunk_from_id('SINF', file_root)
    frame_info = parse_zero.select_chunk_from_id('FRAM', file_root)

    bpy.context.scene.frame_start = frame_info.start_frame
    bpy.context.scene.frame_end = frame_info.end_frame

    bpy.context.scene.render.fps = frame_info.frame_rate
    
    crc_reference = dict()

    for bobj in bpy.data.objects:
        crc_reference.update({ msh2_crc.crc(bobj.name) : bobj.name })


    animation_root = parse_zero.select_chunk_from_id('ANM2', file_root)
    if(animation_root):
        cycle = parse_zero.select_chunk_from_id('CYCL', animation_root)
        kfr_root = parse_zero.select_chunk_from_id('KFR3', animation_root)
        print(len(kfr_root.keyframes), '\n')
        for obj in kfr_root.keyframes:
            print(hex(obj.crc))
            if obj.crc in crc_reference.keys():
                print(crc_reference[obj.crc])

                bpy.data.objects[crc_reference[obj.crc]].animation_data_create()
                action = bpy.data.objects[crc_reference[obj.crc]].animation_data.action = bpy.data.actions.new(name='{0}_Action'.format(crc_reference[obj.crc]))
                loc_x = action.fcurves.new(data_path='location', index=0)
                loc_y = action.fcurves.new(data_path='location', index=1)
                loc_z = action.fcurves.new(data_path='location', index=2)

                loc_x.keyframe_points.add(obj.num_translation_frames)
                loc_y.keyframe_points.add(obj.num_translation_frames)
                loc_z.keyframe_points.add(obj.num_translation_frames)

                rot_w = action.fcurves.new(data_path='rotation_quaternion', index=0)
                rot_x = action.fcurves.new(data_path='rotation_quaternion', index=1)
                rot_y = action.fcurves.new(data_path='rotation_quaternion', index=2)
                rot_z = action.fcurves.new(data_path='rotation_quaternion', index=3)

                rot_w.keyframe_points.add(obj.num_rotation_frames)
                rot_x.keyframe_points.add(obj.num_rotation_frames)
                rot_y.keyframe_points.add(obj.num_rotation_frames)
                rot_z.keyframe_points.add(obj.num_rotation_frames)

                #print(dir(obj))


                for loc_frame in range(obj.num_translation_frames):
                    print(obj.translationDataFrames[loc_frame].index, obj.translationDataFrames[loc_frame].data)
                    
                    f_idx = obj.translationDataFrames[loc_frame].index
                    x, z, y = obj.translationDataFrames[loc_frame].data

                    loc_x.keyframe_points[loc_frame].co = (f_idx, x)
                    loc_y.keyframe_points[loc_frame].co = (f_idx, -y)
                    loc_z.keyframe_points[loc_frame].co = (f_idx, z)

                    #print(loc_frame)

                for rot_frame in range(obj.num_rotation_frames):
                    print(obj.rotationDataFrames[rot_frame].index, obj.rotationDataFrames[rot_frame].data)
                    f_idx = obj.rotationDataFrames[rot_frame].index
                    x, z, y, w = obj.rotationDataFrames[rot_frame].data

                    rot_w.keyframe_points[rot_frame].co = (f_idx, w)
                    rot_x.keyframe_points[rot_frame].co = (f_idx, x)
                    rot_y.keyframe_points[rot_frame].co = (f_idx, -y)
                    rot_z.keyframe_points[rot_frame].co = (f_idx, z)
            else:
                print('CRC_not_found',hex(obj.crc))

def get_mesh_material_index(mesh, ze_idx):
    for i in range(len(mesh.materials)):
        if(mesh.materials[i].ze_material.index == ze_idx):
            return i
    return 0

class HalfEdge():

    def __init__(self, vert, next, flip):
        self.vert = vert
        self.next = next
        self.flip = flip


class ImportZero(bpy.types.Operator, ImportHelper):
    bl_idname = 'scene_zero.importfile'
    bl_label = 'Import Zero Engine (*.msh) File'

    load_objects : bpy.props.BoolProperty(name='Load Objects', default=True)

    load_animations : bpy.props.BoolProperty(name='Load Animations', default=False)

    clear_scene : bpy.props.BoolProperty(name='Clear Scene', default=True)

    def execute(self, context):
        load(self.filepath, self.load_objects, self.load_animations, self.clear_scene)
        return {'FINISHED'}