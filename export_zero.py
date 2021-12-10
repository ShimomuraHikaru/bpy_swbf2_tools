import bpy
import struct
from . import parse_zero
from . import msh2_crc
from bpy_extras.io_utils import ExportHelper

MODL_NULL, \
MODL_GEODYNAMIC, \
MODL_CLOTH, \
MODL_BONE, \
MODL_GEOBONE, \
MODL_GEOSTATIC, \
MODL_GEOSHADOW = range(7)

def build_object(bl_object, parent_chunk):
    modl_chunk = parse_zero.zeroChunk('MODL', 0, parent_chunk)
    
    name=bl_object.name
    chk_name = parse_zero.zeroChunk('NAME', len(name)+(4-len(name)%4),modl_chunk)
    chk_name.data = name
    modl_chunk.addChild(chk_name)

    index = bl_object.ze_object.object_index
    chunk_mndx = parse_zero.zeroChunk('MNDX', 4, modl_chunk)
    chunk_mndx.data = index
    modl_chunk.addChild(chunk_mndx)

    m_type = bl_object.ze_object.object_type #loop to access index proper
    bl_object.ze_object.object_type = m_type

    m_type = bl_object.ze_object['object_type']

    chunk_mtyp = parse_zero.zeroChunk('MTYP', 4, modl_chunk)
    chunk_mtyp.data = m_type
    modl_chunk.addChild(chunk_mtyp)

    parent = bl_object.parent
    if(parent):
        chunk_prnt = parse_zero.zeroChunk('PRNT', len(parent.name)+(4-len(parent.name)%4), modl_chunk)
        chunk_prnt.data = parent.name
        modl_chunk.addChild(chunk_prnt)

    x, y, z = bl_object.location
    location = x, z, -y
    w, x, y, z = bl_object.rotation_quaternion
    rotation = x, z, -y, w
    x, y, z = bl_object.scale
    scale = x, z, y

    chunk_tran = parse_zero.zeroChunk('TRAN', 40, modl_chunk)
    chunk_tran.scale = scale
    chunk_tran.rotation = rotation
    chunk_tran.location = location
    modl_chunk.addChild(chunk_tran)

    hidden = bl_object.ze_object.hidden
    if(hidden):
        chunk_flgs = parse_zero.zeroChunk('FLGS', 4, modl_chunk)
        chunk_flgs.data = 1
        modl_chunk.addChild(chunk_flgs)

    #if certain m_type add geometry and segments
    if(bl_object.type == 'MESH'):
        if(m_type != 2 and m_type != 6 and m_type != 0): # 2 is cloth. 6 is shadow, 0 is Null
            geom_chunk = build_mesh(bl_object, modl_chunk)

            chunk_bbox = parse_zero.zeroChunk('BBOX', 16+12+12+4, geom_chunk)
            chunk_bbox.center, chunk_bbox.extents, chunk_bbox.radius = get_local_bounding_box(bl_object)
            chunk_bbox.rotation = bl_object.rotation_quaternion[:]

            geom_chunk.addChild(chunk_bbox)

            if(len(bl_object.vertex_groups) > 0):
                chunk_envl = parse_zero.zeroChunk('ENVL', len(bl_object.vertex_groups)*4+4, geom_chunk)
                chunk_envl.count = len(bl_object.vertex_groups)
                data = []
                for group in bl_object.vertex_groups:
                    for o in bpy.context.scene.objects:
                        if(group.name == o.name):
                            data.append(bpy.context.scene.objects[group.name].ze_object.object_index)
                    
                assert len(data) == len(bl_object.vertex_groups), 'Error: There must be an object of same name for every vertex group'
                chunk_envl.data = data
                geom_chunk.addChild(chunk_envl)

            modl_chunk.addChild(geom_chunk)

        if(m_type == 6):
            geom_chunk = build_shadow_mesh(bl_object, modl_chunk)
            modl_chunk.addChild(geom_chunk)

        if(m_type == 2): # cloth
            geom_chunk = build_cloth_mesh(bl_object, modl_chunk)
            
            chunk_bbox = parse_zero.zeroChunk('BBOX', 16+12+12+4, geom_chunk)
            chunk_bbox.center, chunk_bbox.extents, chunk_bbox.radius = get_local_bounding_box(bl_object)
            chunk_bbox.rotation = bl_object.rotation_quaternion[:]
            
            if(len(bl_object.vertex_groups) > 0):
                chunk_envl = parse_zero.zeroChunk('ENVL', len(bl_object.vertex_groups)*4+4, geom_chunk)
                chunk_envl.count = len(bl_object.vertex_groups)
                data = []
                for group in bl_object.vertex_groups:
                    for o in bpy.context.scene.objects:
                        if(group.name == o.name):
                            data.append(bpy.context.scene.objects[group.name].ze_object.object_index)
                assert len(data) == len(bl_object.vertex_groups), 'Error: There must be an object of same name for every vertex group'
                chunk_envl.data = data
                geom_chunk.addChild(chunk_envl)

            geom_chunk.addChild(chunk_bbox)

            modl_chunk.addChild(geom_chunk)


    coll_prim = bl_object.ze_object.collision
    if(coll_prim):
        bl_object.ze_object.collision_type = bl_object.ze_object.collision_type
        chunk_swci = parse_zero.zeroChunk('SWCI', 16, modl_chunk)
        chunk_swci.type = bl_object.ze_object['collision_type']
        chunk_swci.x = bl_object.ze_object.collision_x
        chunk_swci.y = bl_object.ze_object.collision_y
        chunk_swci.z = bl_object.ze_object.collision_z
        modl_chunk.addChild(chunk_swci)
    
    return modl_chunk

def build_top_level(export_animations):

    chunk_hedr = parse_zero.zeroChunk('HEDR', 0, None)
    chunk_msh2 = parse_zero.zeroChunk('MSH2', 0, chunk_hedr)
    chunk_hedr.addChild(chunk_msh2)
    

    # scene info
    scene = bpy.context.scene
    chunk_sinf = parse_zero.zeroChunk('SINF', 0, chunk_msh2)
    s_name = bpy.context.scene.name
    chunk_s_name = parse_zero.zeroChunk('NAME', len(s_name)+(4-len(s_name)%4), chunk_sinf)
    chunk_s_name.data = s_name
    chunk_sinf.addChild(chunk_s_name)

    chunk_fram = parse_zero.zeroChunk('FRAM', 12, chunk_sinf)
    chunk_fram.start = scene.frame_start
    chunk_fram.end = scene.frame_end
    chunk_fram.rate = scene.render.fps / scene.render.fps_base
    chunk_sinf.addChild(chunk_fram)
    chunk_msh2.addChild(chunk_sinf)

    chunk_bbox = parse_zero.zeroChunk('BBOX', 16+12+12+4, chunk_sinf)
    rotation = (0.0, 0.0, 0.0, 1.0)
    center, extents, radius = get_scene_bounding_box()
    chunk_bbox.rotation = rotation
    chunk_bbox.center = center
    chunk_bbox.extents = extents
    chunk_bbox.radius = radius

    chunk_sinf.addChild(chunk_bbox)

    # material info
    matl = build_material_list(chunk_msh2)
    chunk_msh2.addChild(matl)
    # model info
    exportable_objects = [obj for obj in bpy.context.scene.objects if obj.type == 'EMPTY' or obj.type == 'MESH']

    for i in range(len(exportable_objects)):
        ob = None
        for j in range(len(exportable_objects)):
            if(i+1 == exportable_objects[j].ze_object.object_index):
                ob = exportable_objects[j]
                break
        assert ob != None, 'Object Indices Incorrect: Recalculate Indices'

        chunk_modl = build_object(ob, chunk_msh2)
        chunk_msh2.addChild(chunk_modl)
    if(export_animations == True):
        build_animation_data(chunk_hedr)
    
    chunk_cl1l = parse_zero.zeroChunk('CL1L', 0, chunk_hedr)
    chunk_hedr.addChild(chunk_cl1l)
    return chunk_hedr

def build_material_list(parent_chunk):

    chunk_matl = parse_zero.zeroChunk('MATL', 4, parent_chunk)
    for i in range(len(bpy.data.materials)):
        mat = None
        for j in range(len(bpy.data.materials)):
            if(i == bpy.data.materials[j].ze_material.index):
                mat = bpy.data.materials[j]
                break
        assert mat != None, 'Material Indices Incorrect: Recalculate Indices'


        chunk_matd = parse_zero.zeroChunk('MATD', 0, chunk_matl)
        
        chunk_name = parse_zero.zeroChunk('NAME', len(mat.name)+(4-len(mat.name)%4), chunk_matd)
        chunk_name.data = mat.name
        
        chunk_data = parse_zero.zeroChunk('DATA', 16*3+4, chunk_matd)
        chunk_data.diffuse = mat.ze_material.diffuse[:]
        chunk_data.ambient = mat.ze_material.ambient[:]
        chunk_data.specular = mat.ze_material.specular[:]
        chunk_data.specular_strength = mat.ze_material.specular_sharpness

        chunk_atrb = parse_zero.zeroChunk('ATRB', 4, chunk_matd)

        
        fl = mat.ze_material.flags
        mat.ze_material.flags = fl

        rt = mat.ze_material.render_type
        mat.ze_material.render_type = rt

        chunk_atrb.flags = mat.ze_material['flags']
        chunk_atrb.render_type = mat.ze_material['render_type']
        chunk_atrb.data0 = mat.ze_material.data1 
        chunk_atrb.data1 = mat.ze_material.data2

        chunk_matd.addChild(chunk_name)
        chunk_matd.addChild(chunk_data)
        chunk_matd.addChild(chunk_atrb)

        if(mat.ze_material.texture1 != None):
            tex1_name = mat.ze_material.texture1.name
            #print(tex1_name)
            chunk_tx0d = parse_zero.zeroChunk('TX0D', len(tex1_name)+(4-len(tex1_name)%4), chunk_matd)
            chunk_tx0d.data = tex1_name
            chunk_matd.addChild(chunk_tx0d)

        chunk_matl.addChild(chunk_matd)
        chunk_matl.data = len(chunk_matl.children)

    return chunk_matl



def build_mesh(bl_object, parent_chunk):

    chunk_geom = parse_zero.zeroChunk('GEOM', 0, parent_chunk)
    
    poly_seg_list=[]
    vert_seg_list=[]
    uv_seg_list=[]
# gather indices
    #use faces and material index as foundation for SEGM chunk
    assert len(bl_object.data.materials) > 0, "All Exported meshes mush have a material assigned"
    for i in range(len(bl_object.data.materials)):
        print(i)
        segpolys = None
        for poly in bl_object.data.polygons:
            if(poly.material_index == i):
                if(segpolys == None):
                    segpolys = []
                segpolys.append(poly)
        if(segpolys != None):
            poly_seg_list.append(segpolys)
            for dbgseg1 in poly_seg_list:
                for dbgpoly in dbgseg1:
                    print(dbgpoly.vertices[:])

    for seg in poly_seg_list:
        vert_list = None
        used_vert_indices = set()
        if(seg != None):
            for poly in seg:
                for idx in poly.vertices:
                    if idx not in used_vert_indices:
                        if(vert_list == None):
                            vert_list=[]
                        vert_list.append(idx)
                        used_vert_indices.add(idx)
            vert_list.sort()
            vert_seg_list.append(vert_list)
            
    #print('Vert: \n', vert_seg_list[i])

    #used_uv_indices = None
    for vert_seg in vert_seg_list:
        uv_list = None
        for vert in vert_seg:
            j = 0
            for loop in bl_object.data.loops:
                if(loop.vertex_index == vert):
                    if(uv_list == None):
                        uv_list = []
                    uv_list.append(j)
                    #used_uv_indices.add(i)
                    break
                j+=1
        
        if(uv_list != None):
            uv_seg_list.append(uv_list)
    assert(len(poly_seg_list) > 0), 'Error: line 183: poly_seg_list is empty'
    for k in range(len(poly_seg_list)):
        assert poly_seg_list[k] != None, 'Error: SEGM {0}: No polygons exported in this segm'.format(k)

        chunk_segm = parse_zero.zeroChunk('SEGM', 0, chunk_geom)
        final_vertex_buffer = []
        final_normal_buffer = []
        final_weight_buffer = []
        for vert in vert_seg_list[k]:
                    
            x, y, z = bl_object.data.vertices[vert].co
            final_normal_buffer.append(bl_object.data.vertices[vert].normal[:])
            
            p = 0
            while(p < 4):
                grp = bl_object.data.vertices[vert].groups
                if p in range(len(grp)):
                    final_weight_buffer.append((grp[p].group, grp[p].weight))
                else:
                    final_weight_buffer.append((0, 0.0))
                p+=1


            vert = x, z, -y
            final_vertex_buffer.append(vert)

        final_poly_buffer = []
        #converts the poly list to current
        for poly in poly_seg_list[k]:
            assert len(poly.vertices) == 3, "Export Failed partway through.\nGeometry must be in triangles unless shadow"

            for idx in range(len(poly.vertices)):
                for j in range(len(vert_seg_list[k])):
                    if(poly.vertices[idx] == vert_seg_list[k][j]):
                        poly.vertices[idx] = j
                        break
            final_poly_buffer.append(tuple([poly.vertices[0], poly.vertices[1], poly.vertices[2]]))

        final_uv_buffer = []
        if(len(bl_object.data.uv_layers) > 0):
            for uv_idx in uv_seg_list[k]:
                final_uv_buffer.append(bl_object.data.uv_layers.active.data[uv_idx].uv[:])

        chunk_mati = parse_zero.zeroChunk('MATI', 4, chunk_segm)
        chunk_mati.data = bl_object.data.materials[poly_seg_list[k][0].material_index].ze_material.index

        chunk_posl = parse_zero.zeroChunk('POSL', (len(final_vertex_buffer)*3*4)+4, chunk_segm)
        chunk_posl.count = len(final_vertex_buffer)
        chunk_posl.data = final_vertex_buffer

        chunk_nrml = parse_zero.zeroChunk('NRML', (len(final_normal_buffer*3*4)+4), chunk_segm)
        chunk_nrml.count = len(final_normal_buffer)
        chunk_nrml.data = final_normal_buffer

        chunk_ndxt = parse_zero.zeroChunk('NDXT', 4+(  len(final_poly_buffer)*len(final_poly_buffer[0])*2 ), chunk_segm)
        chunk_ndxt.count = len(final_poly_buffer)
        chunk_ndxt.data = final_poly_buffer

        chunk_strp = build_strips(final_poly_buffer, chunk_segm)

        #print(final_poly_buffer)

        chunk_segm.addChild(chunk_mati)
        chunk_segm.addChild(chunk_posl)
        chunk_segm.addChild(chunk_nrml)
        chunk_segm.addChild(chunk_ndxt)
        chunk_segm.addChild(chunk_strp)
        if(len(bl_object.vertex_groups) > 0):
            chunk_wght = parse_zero.zeroChunk('WGHT', 4+(len(final_weight_buffer)*8), chunk_segm)
            chunk_wght.count = len(final_weight_buffer)//4
            chunk_wght.data = final_weight_buffer
            chunk_segm.addChild(chunk_wght)
        
        if(len(bl_object.data.uv_layers) > 0):    
            chunk_uv0l = parse_zero.zeroChunk('UV0L', 4+(len(final_uv_buffer)*4*2), chunk_segm)
            chunk_uv0l.count = len(final_uv_buffer)
            chunk_uv0l.data = final_uv_buffer
            chunk_segm.addChild(chunk_uv0l)

        chunk_geom.addChild(chunk_segm)
        #print('Debug line 239: \n', chunk_geom)
            
    return chunk_geom

def build_cloth_mesh(bl_object, chunk_parent):
    chunk_geom = parse_zero.zeroChunk('GEOM', 0, chunk_parent)
    chunk_clth = parse_zero.zeroChunk('CLTH', 0, chunk_geom)

    polys = [list(poly.vertices[:]) for poly in bl_object.data.polygons]
    for poly in polys:
        assert len(poly) == 3, 'Cloth: Error: Cloth polys must be triangles.'
        poly.reverse()
    polys = [tuple(poly) for poly in polys]
    
    verts = [(vert.co[0], vert.co[2], -vert.co[1]) for vert in bl_object.data.vertices]

    uv_list = None
    for vert in bl_object.data.vertices:
        j = 0
        for loop in bl_object.data.loops:
            if(loop.vertex_index == vert.index):
                if(uv_list == None):
                    uv_list = []
                uv_list.append(bl_object.data.uv_layers.active.data[j].uv[:])
                #used_uv_indices.add(i)
                break
            j+=1

    weights = []            
    for i in range(len(bl_object.ze_cloth_fixed_points)):
        fxp = bl_object.ze_cloth_fixed_points[i]
        vert = bl_object.data.vertices[fxp.value]
        group = vert.groups[0].group
        weights.append(bl_object.vertex_groups[group].name)
    assert len(weights) == len(bl_object.ze_cloth_fixed_points), 'If there are weights all vertices must be weighted'

    weight_data = b''
    weight_data += struct.pack('<I', len(weights))
    for n in weights:
        weight_data += struct.pack('{}sx'.format(len(n)), n.encode())

    weight_data_size = len(weight_data) + (4 - len(weight_data)%4)
    for i in range(weight_data_size-len(weight_data)):
        weight_data += b'\x00'


    chunk_cpos = parse_zero.zeroChunk('CPOS', 4+(len(bl_object.data.vertices)*4*3), chunk_clth)
    chunk_cpos.count = len(verts)
    chunk_cpos.data = verts

    chunk_clth.addChild(chunk_cpos)
    
    chunk_cmsh = parse_zero.zeroChunk('CMSH', 4+(len(polys)*4*3), chunk_clth)
    chunk_cmsh.count = len(polys)
    chunk_cmsh.data = polys

    chunk_clth.addChild(chunk_cmsh)
    
    if(bl_object.data.uv_layers.active != None):
        chunk_cuv0 = parse_zero.zeroChunk('CUV0', 4+len(uv_list)*4*2, chunk_clth)
        chunk_cuv0.count = len(uv_list)
        chunk_cuv0.data = uv_list

        chunk_clth.addChild(chunk_cuv0)

    if(bl_object.ze_object.clth_texture != None):
        tex = bl_object.ze_object.clth_texture
        chunk_ctex = parse_zero.zeroChunk('CTEX', len(tex.name)+(4-len(tex.name)%4), chunk_clth)
        chunk_ctex.data = tex.name
        chunk_clth.addChild(chunk_ctex)

    if(len(bl_object.ze_cloth_fixed_points) > 0):
        chunk_fidx = parse_zero.zeroChunk('FIDX', 4+(len(bl_object.ze_cloth_fixed_points)*4), chunk_clth)
        chunk_fidx.data = [vert.value for vert in bl_object.ze_cloth_fixed_points]
        chunk_fidx.count = len(chunk_fidx.data)
        chunk_clth.addChild(chunk_fidx)

        if(len(bl_object.vertex_groups) > 0):
            chunk_fwgt = parse_zero.zeroChunk('FWGT', weight_data_size, chunk_clth)
            chunk_fwgt.data = weight_data
            chunk_fwgt.count = len(chunk_fidx.data)
            chunk_clth.addChild(chunk_fwgt)

    if(len(bl_object.ze_cloth_stretch_constraints) > 0):
        chunk_sprs = parse_zero.zeroChunk('SPRS', 4+(len(bl_object.ze_cloth_stretch_constraints)*2*2), chunk_clth)
        chunk_sprs.data = [vert.value[:] for vert in bl_object.ze_cloth_stretch_constraints]
        chunk_sprs.count = len(chunk_sprs.data)
        chunk_clth.addChild(chunk_sprs)


    if(len(bl_object.ze_cloth_cross_constraints) > 0):    
        chunk_cprs = parse_zero.zeroChunk('CPRS', 4+(len(bl_object.ze_cloth_cross_constraints)*2*2), chunk_clth)
        chunk_cprs.data = [vert.value[:] for vert in bl_object.ze_cloth_cross_constraints]
        chunk_cprs.count = len(chunk_cprs.data)
        chunk_clth.addChild(chunk_cprs)

    if(len(bl_object.ze_cloth_bend_constraints) > 0):
        chunk_bprs = parse_zero.zeroChunk('BPRS', 4+(len(bl_object.ze_cloth_bend_constraints)*2*2), chunk_clth)
        chunk_bprs.data = [vert.value[:] for vert in bl_object.ze_cloth_bend_constraints]
        chunk_bprs.count = len(chunk_bprs.data)
        chunk_clth.addChild(chunk_bprs)

    if(len(bl_object.ze_cloth_collision_objects) > 0):
        data = b''
        data += struct.pack('<I', len(bl_object.ze_cloth_collision_objects))
        for item in bl_object.ze_cloth_collision_objects:
            data += struct.pack('{}sx'.format(len(item.ob.name)), item.ob.name.encode())
            data += struct.pack('{}sx'.format(len(item.ob.parent.name)), item.ob.parent.name.encode())
            item.ob_type = item.ob_type
            data += struct.pack('<I', item['ob_type'])
            if(item.ob_type == 2):
                data += struct.pack('<3f', item.x/2, item.y/2, item.z/2)
            else:
                data += struct.pack('<3f', item.x, item.y, item.z)

        data_size = len(data) + (4- len(data)%4)
        for i in range(data_size - len(data)):
            data += b'\x00'

        chunk_coll = parse_zero.zeroChunk('COLL', data_size, chunk_clth)
        chunk_coll.count = len(bl_object.ze_cloth_collision_objects)
        chunk_coll.data = data
        chunk_clth.addChild(chunk_coll)
    
    chunk_geom.addChild(chunk_clth)
    return chunk_geom

def build_shadow_mesh(bl_object, chunk_parent):
    chunk_geom = parse_zero.zeroChunk('GEOM', 0, chunk_parent)
    half_edges = []
    for i in range(len(bl_object.data.edges)*2):
        rev_idx = 0
        vert = bl_object.data.edges[i//2].vertices[i%2]
        if(i%2 == 1):
            rev_idx = i-1
        else:
            rev_idx = i+1
        half_edges.append([vert, 0, rev_idx, 0xFFFF])

    for poly in bl_object.data.polygons:
        #traverse the polymesh backwards
        i = len(poly.loop_indices)-1
        indices = poly.loop_indices[:]
        loops = [bl_object.data.loops[l] for l in indices]
        poly_verts = [v for v in poly.vertices]

        #print(poly_verts)
        while(i > -1): 
            base_index = loops[i].edge_index*2
            if(half_edges[base_index][0] != poly_verts[i]):
                base_index += 1
            target_index = loops[i-1].edge_index*2
            if(half_edges[target_index][0] != poly_verts[i-1]):
                target_index += 1
            
            half_edges[base_index][1] = target_index

            #print(loops[i].edge_index*2)
            #print(bl_object.data.edges[loops[i].edge_index].vertices[:])
            i-=1
       #print('\n')
    
    final_half_edges = [tuple(e) for e in half_edges]
    final_vertices = [(v.co[0], v.co[2], -v.co[1]) for v in bl_object.data.vertices]
    for i in range(len(final_half_edges)):
        edge = final_half_edges[i]
        print(i, edge)

    shadow_size = 8+(len(final_vertices)*4*3)+(len(final_half_edges)*2*4)
    chunk_shdw= parse_zero.zeroChunk('SHDW', shadow_size, chunk_geom)
    chunk_shdw.num_verts = len(final_vertices)
    chunk_shdw.verts = final_vertices
    chunk_shdw.num_edges = len(final_half_edges)
    chunk_shdw.edges = final_half_edges

    chunk_geom.addChild(chunk_shdw)

    return chunk_geom

def build_strips(polys, chunk_parent):
    strips = []
    data = b''
    """
    new_strip = True
    temp_strip = []
    i = 0
    while(i < len(polys)):
        print('tempstrip', temp_strip)
        if(new_strip == True):
            temp_strip = []
            temp_strip.extend(list(polys[i]))
            new_strip = False
            print('newstrip', temp_strip)
        else:
            vertex_count = 0
            index = 0
            for j in polys[i-1]:
                if(j in polys[i]):
                    vertex_count += 1

            if(vertex_count < 2):
                temp_strip[0] = temp_strip[0] | 0x8000
                temp_strip[1] = temp_strip[1] | 0x8000
                strips.append(temp_strip)
                print('append strip', strips)
                new_strip = True
                i -= 1 # start over from this one
            else:
                for k in polys[i]:
                    if(k not in temp_strip):
                        temp_strip.append(k)
                        print('append indice', temp_strip)
        i+=1

    """
    for i in range(len(polys)):
        tri = list(polys[i])
        tri[0] = tri[0] | 0x8000
        tri[1] = tri[1] | 0x8000
        strips.append(tri)
        
    for strp in strips:
        data += struct.pack('<{}H'.format(len(strp)), *strp)

    chunk_strp = parse_zero.zeroChunk('STRP', len(data)+4, chunk_parent)
    chunk_strp.count = len(data)//2
    chunk_strp.data = data
    return chunk_strp

def get_local_bounding_box(bl_object):
    verts_x = [vert[0] for vert in bl_object.bound_box]
    verts_y = [vert[1] for vert in bl_object.bound_box]
    verts_z = [vert[2] for vert in bl_object.bound_box]

    min_x = min(verts_x)
    max_x = max(verts_x)

    min_y = min(verts_y)
    max_y = max(verts_y)

    min_z = min(verts_z)
    max_z = max(verts_z)

    center_x = (min_x + max_x)/2
    center_y = (min_y + max_y)/2
    center_z = (min_z + max_z)/2

    center = (center_x, center_z, -center_y)

    extent_x = (abs(min_x)+abs(max_x))/2
    extent_y = (abs(min_y)+abs(max_y))/2
    extent_z = (abs(min_z)+abs(max_z))/2

    extents = (extent_x, extent_z, extent_y)

    radius = (min(extents))

    return (center, extents, radius)


def get_world_bounding_box(bl_object):
    verts_x = [vert[0] for vert in bl_object.bound_box]
    verts_y = [vert[1] for vert in bl_object.bound_box]
    verts_z = [vert[2] for vert in bl_object.bound_box]

    min_x = min(verts_x) + bl_object.location[0]
    max_x = max(verts_x) + bl_object.location[0]

    min_y = min(verts_y) + bl_object.location[1]
    max_y = max(verts_y) + bl_object.location[1]

    min_z = min(verts_z) + bl_object.location[2]
    max_z = max(verts_z) + bl_object.location[2]

    return (min_x, max_x, min_y, max_y, min_z, max_z)

def get_scene_bounding_box():
    objs = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH' or obj.type == 'EMPTY']
    bbs = []
    for ob in objs:
        bbs.append(get_world_bounding_box(ob))
        print(len(bbs))

    verts_min_x = [min_max[0] for min_max in bbs]
    verts_min_y = [min_max[2] for min_max in bbs]
    verts_min_z = [min_max[4] for min_max in bbs]

    verts_max_x = [min_max[1] for min_max in bbs]
    verts_max_y = [min_max[3] for min_max in bbs]
    verts_max_z = [min_max[5] for min_max in bbs]

    min_x = min(verts_min_x)
    min_y = min(verts_min_y)
    min_z = min(verts_min_z)

    max_x = min(verts_max_x)
    max_y = min(verts_max_y)
    max_z = min(verts_max_z)

    center_x = (min_x + max_x)/2
    center_y = (min_y + max_y)/2
    center_z = (min_z + max_z)/2

    center = (center_x, center_z, -center_y)

    extent_x = (abs(min_x)+abs(max_x))/2
    extent_y = (abs(min_y)+abs(max_y))/2
    extent_z = (abs(min_z)+abs(max_z))/2

    extents = (extent_x, extent_z, extent_y)

    radius = (min(extents))

    return (center, extents, radius)

def build_animation_data(root_chunk):

    skeleton_data = []
    blend_factor_data = []
    keyframe_data = b''
    obj_list = [obj for obj in bpy.context.scene.objects if \
        obj.ze_object.chain_object == True and obj.type == 'MESH' \
        or obj.ze_object.chain_object == True and obj.type == 'EMPTY']
    for obj in obj_list:
        crc = msh2_crc.crc(obj.name)
        skeleton_data.append((crc, 0, obj.ze_object.constraint, 0, 0))
        blend_factor_data.append((crc, obj.ze_object.blend_factor))
        assert obj.animation_data != None, 'No animation data for chain item: {}'.format(obj.name)
        act = obj.animation_data.action
        location_data = [f for f in act.fcurves if f.data_path == 'location']
        rotation_data = [f for f in act.fcurves if f.data_path == 'rotation_quaternion']
        assert len(location_data) > 0 and len(rotation_data) > 0, \
        'Animation data does not exist for chain item: {}. Make sure rotation mode is set to QUATERNION'.format(obj.name)
        start = bpy.context.scene.frame_start
        end = bpy.context.scene.frame_end

        for fc in location_data:
            assert len(fc.keyframe_points) == (end - start) + 1, 'Needs Keyframes on every frame: Bake animation'
        for fc in rotation_data:
            assert len(fc.keyframe_points) == (end - start) + 1, 'Needs Keyframes on every frame: Bake animation'

        loc_keys = []
        rot_keys = []
        for i in range(end-start+1):
            loc_x = location_data[0].keyframe_points[i].co[1]
            loc_y = location_data[2].keyframe_points[i].co[1]
            loc_z = -location_data[1].keyframe_points[i].co[1]

            rot_x = rotation_data[1].keyframe_points[i].co[1]
            rot_y = rotation_data[3].keyframe_points[i].co[1]
            rot_z = -rotation_data[2].keyframe_points[i].co[1]
            rot_w = rotation_data[0].keyframe_points[i].co[1]

            loc_keys.append((loc_x, loc_y, loc_z))
            rot_keys.append((rot_x, rot_y, rot_z, rot_w))


        keyframe_data += struct.pack('<2I', crc, 0) # second arg 0 is keyframe type
        keyframe_data += struct.pack('<2I', len(loc_keys), len(rot_keys))
        for i in range(len(loc_keys)):
            keyframe_data += struct.pack('<I3f', i, *loc_keys[i])
        for i in range(len(rot_keys)):
            keyframe_data += struct.pack('<I4f', i, *rot_keys[i])
    
    chunk_skl2 = parse_zero.zeroChunk('SKL2', 4+len(skeleton_data)*4*5, root_chunk)
    chunk_skl2.count = len(skeleton_data)
    chunk_skl2.data = skeleton_data

    chunk_bln2 = parse_zero.zeroChunk('BLN2', 4+len(blend_factor_data)*8, root_chunk)
    chunk_bln2.count = len(blend_factor_data)
    chunk_bln2.data = blend_factor_data

    chunk_anm2 = parse_zero.zeroChunk('ANM2', 0, root_chunk)

    chunk_cycl = parse_zero.zeroChunk('CYCL', 4*5+64, root_chunk)
    chunk_cycl.count = 1
    chunk_cycl.ani_name = 'fullanimation' # length 13
    chunk_cycl.frame_rate = bpy.context.scene.render.fps / \
        bpy.context.scene.render.fps_base

    chunk_cycl.play_style = 0
    chunk_cycl.first_frame = bpy.context.scene.frame_start
    chunk_cycl.last_frame = bpy.context.scene.frame_end

    
    chunk_kfr3 = parse_zero.zeroChunk('KFR3', 4+len(keyframe_data), root_chunk)
    chunk_kfr3.count = len(skeleton_data)
    chunk_kfr3.data = keyframe_data

    chunk_anm2.addChild(chunk_cycl)
    chunk_anm2.addChild(chunk_kfr3)

    root_chunk.addChild(chunk_skl2)
    root_chunk.addChild(chunk_bln2)
    root_chunk.addChild(chunk_anm2)



def write_chunk(file, chunk, dict_formats):
    write_chunk_tag(file, chunk)
    write_chunk_data(file, chunk, dict_formats)

def write_chunk_tag(file, chunk):
    file.write(struct.pack('<4sI', chunk.name.encode(), chunk.size_in_bytes))

def write_chunk_data(file, chunk, dict_formats, pad_string = True):
    if(dict_formats != None):
        for key in dict_formats.keys():
            if(key in chunk.__dict__.keys()):
                if(isinstance(chunk.__dict__[key], list)):
                    for item in chunk.__dict__[key]:
                        if(isinstance(item, tuple)):    
                            file.write(struct.pack('<{0}'.format(dict_formats[key]),
                            *item))
                        else:
                            file.write(struct.pack('<{0}'.format(dict_formats[key]),
                            item))
                elif(isinstance(chunk.__dict__[key], str)):
                    if(pad_string == True):
                        file.write(struct.pack(dict_formats[key].format(len(chunk.__dict__[key]),
                        4-len(chunk.__dict__[key])%4), chunk.__dict__[key].encode()))
                    else:
                        file.write(struct.pack(dict_formats[key].format(len(chunk.__dict__[key])), chunk.__dict__[key].encode()))
                
                elif(isinstance(chunk.__dict__[key], bytes)):
                    file.write(chunk.__dict__[key])

                else:
                    if(isinstance(chunk.__dict__[key], tuple)):
                        file.write(struct.pack('<{0}'.format(dict_formats[key]),
                        *chunk.__dict__[key]))
                    else:
                        file.write(struct.pack('<{0}'.format(dict_formats[key]),
                        chunk.__dict__[key]))


def write_msh_to_file(filepath, export_animations):
    with open(filepath, 'wb') as file:
        root_chunk = build_top_level(export_animations)
        root_chunk.update_size_from_children()
        write_recursive(file, root_chunk, None)

def write_recursive(file, chunk, dict_formats):
    #print('Exporting: \n{0}\n'.format(chunk))
    write_chunk(file, chunk, parse_zero.zero_id_dict[chunk.name][1])
    if(chunk.children):
        for child in chunk.children:
            write_recursive(file, child, parse_zero.zero_id_dict[chunk.name][1])

class ExportZero(bpy.types.Operator, ExportHelper):
    bl_idname = 'scene_zero.exportfile'
    bl_label = 'Export Zero Engine (*.msh) File'

    filename_ext = '.msh'

    export_animations = bpy.props.BoolProperty(name='Export Animations',default=False)

    def execute(self, context):
        write_msh_to_file(self.filepath, self.export_animations)
        return {'FINISHED'}
        