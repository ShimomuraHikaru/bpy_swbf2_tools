# initialization for blender

import bpy
from . import import_zero
from . import export_zero

bl_info = {
    'name':'SWBF2 Msh File',
    'description':'Imports and exports a Star Wars BattleFront 2 ZeroEngine Msh File',
    'category':'Import-Export',
    'author':'Joshua Thompson',
    'version':(0,0,5),
    'blender':(2, 80, 0),
    'location':'File > Import/Export > zero engine',
    'support':'OFFICIAL',
    'doc_url':'',
    'warning':''
}

class BindArmatureToZeroSkeletonRotation(bpy.types.Operator):
    bl_idname = 'object.ze_bind_armature_rot'
    bl_label = 'Bind Proxy Armature To Node Rotation'
    bl_options = {'REGISTER', 'UNDO'}

    owner_space : bpy.props.EnumProperty(items=[
        ('WORLD', 'WORLD', 'WORLD'),
        ('LOCAL', 'LOCAL', 'LOCAL')
    ], default='WORLD')

    target_space : bpy.props.EnumProperty(items=[
        ('WORLD', 'WORLD', 'WORLD'),
        ('LOCAL', 'LOCAL', 'LOCAL')
        ], default='WORLD')

    @classmethod
    def poll(cls, context):
        return context.active_object.type == 'ARMATURE' and context.object.mode == 'POSE'

    def execute(self, context):
        bones = context.selected_pose_bones[:]
        for bone in bones:
            cst = bone.constraints.new(type='COPY_ROTATION')
            cst.target = context.scene.objects[bone.name]
            cst.owner_space = self.owner_space
            cst.target_space = self.target_space

        return {'FINISHED'}

class BindArmatureToZeroSkeletonLocation(bpy.types.Operator):
    bl_idname = 'object.ze_bind_armature_loc'
    bl_label = 'Bind Proxy Armature To Node Location'
    bl_options = {'REGISTER', 'UNDO'}

    owner_space : bpy.props.EnumProperty(items=[
        ('WORLD', 'WORLD', 'WORLD'),
        ('LOCAL', 'LOCAL', 'LOCAL')
    ], default='WORLD')

    target_space : bpy.props.EnumProperty(items=[
        ('WORLD', 'WORLD', 'WORLD'),
        ('LOCAL', 'LOCAL', 'LOCAL')
    ], default='WORLD')


    @classmethod
    def poll(cls, context):
        return context.active_object.type == 'ARMATURE' and context.object.mode == 'POSE'

    def execute(self, context):
        for bone in context.selected_pose_bones:    
            cst = bone.constraints.new('COPY_LOCATION')
            cst.target = bpy.data.objects[bone.name]
            cst.owner_space = self.owner_space
            cst.target_space = self.target_space

        return {'FINISHED'}

class BindZeroSkeletonToProxy_ROT(bpy.types.Operator):
    bl_idname = 'object.bind_skel'
    bl_label = 'Bind Skeleton Nodes To Armature Rotation'

    @classmethod
    def poll(cls, context):
        o_type = context.active_object.type
        return o_type == 'EMPTY' or o_type == 'MESH'

    def execute(self, context):
        for obj in context.selected_objects:
            arm = context.scene.objects['Zero_Proxy']
            bone_names = [b.name for b in arm.data.bones]
            if(obj.name in bone_names):
                cst = obj.constraints.new(type='COPY_ROTATION')
                cst.target = arm
                cst.subtarget = obj.name

        return {'FINISHED'}

class BindZeroSkeletonToProxy_LOC(bpy.types.Operator):
    bl_idname = 'object.bind_skel_loc'
    bl_label = 'Bind Skeleton Nodes To Armature Location'

    @classmethod
    def poll(cls, context):
        o_type = context.active_object.type
        return o_type == 'EMPTY' or o_type == 'MESH'

    def execute(self, context):
        for obj in context.selected_objects:
            arm = context.scene.objects['Zero_Proxy']
            bone_names = [b.name for b in arm.data.bones]
            if(obj.name in bone_names):
                cst = obj.constraints.new(type='COPY_LOCATION')
                cst.target = arm
                cst.subtarget = obj.name

        return {'FINISHED'}



class ZeroSetSceneIndices(bpy.types.Operator):
    bl_label = 'Set Indices'
    bl_idname = 'object.ze_indices_set'
    
    def trace_heirarchy(self, bl_object, ob_list):
        ob_list.append(bl_object)
        for child in bl_object.children:
            if(child.type == 'MESH' or child.type == 'EMPTY'):
                self.trace_heirarchy(child, ob_list)
    
    def execute(self, context):
        exportable_objects = [obj for obj in context.scene.objects if obj.type == 'MESH' or obj.type == 'EMPTY']
        
        root_object = None
            
        num_roots = 0
        for ob in exportable_objects:
            if(ob.parent == None):
                num_roots += 1
                root_object = ob
                    
        assert num_roots == 1, 'Error: Cannot Set Indices, There can be only one root object'
        if(root_object):
            ob_list = []
            self.trace_heirarchy(root_object, ob_list)
            for i in range(len(ob_list)):
                ob_list[i].ze_object.object_index = i+1
        

        for i in range(len(bpy.data.materials)):
            bpy.data.materials[i].ze_material.index = i

        return {'FINISHED'}

class ZeroSetObjectTypeSelection(bpy.types.Operator):
    bl_label = 'Set Object Type'
    bl_idname = 'object.ze_selection_type_set'
    bl_options = {'REGISTER', 'UNDO'}
    
    select_type : bpy.props.EnumProperty(name='MODL Type', items = [
    ('null', 'Null', 'An absolute null object'),
    ('geodynamic', 'Dynamic', 'A mesh object that contains envelopes and constrains'),
    ('cloth', 'Cloth', 'Obviously Cloth'),
    ('bone', 'Bone', 'An animated Null'),
    ('geobone', 'Animated', 'a non-enveloped animated mesh'),
    ('staticgeo', 'Static Geometry', 'Plain Geometry'),
    ('shadowgeo', 'Shadow Geometry', 'Shadow'),
    ])

    @classmethod
    def poll(cls, context):
        return len(context.selected_objects) > 0

    def execute(self, context):
        for ob in context.selected_objects:
            ob.ze_object.object_type = self.select_type

        return {'FINISHED'}

class ZeroContextMenu(bpy.types.Menu):
    bl_label = 'Zero Engine'
    bl_idname = 'VIEW3D_MT_zero_engine'

    def draw(self, context):
        layout = self.layout
        if(context.object.mode == 'OBJECT'):
            layout.operator(ZeroSetSceneIndices.bl_idname)
            layout.operator(ZeroSetObjectTypeSelection.bl_idname)
            layout.operator(BindZeroSkeletonToProxy_LOC.bl_idname)
            layout.operator(BindZeroSkeletonToProxy_ROT.bl_idname)
        if(context.object.mode == 'POSE'):
            layout.operator(BindArmatureToZeroSkeletonRotation.bl_idname)
            layout.operator(BindArmatureToZeroSkeletonLocation.bl_idname)

def draw_zero_menu(self, context):
    layout = self.layout
    layout.menu(ZeroContextMenu.bl_idname)

tool_ops = [
    ZeroContextMenu,
    ZeroSetSceneIndices,
    ZeroSetObjectTypeSelection,

    BindArmatureToZeroSkeletonRotation,
    BindArmatureToZeroSkeletonLocation,
    BindZeroSkeletonToProxy_ROT,
    BindZeroSkeletonToProxy_LOC
]

class ClothFixedPointProp(bpy.types.PropertyGroup):
    value : bpy.props.IntProperty()

class ClothStretchConstraint(bpy.types.PropertyGroup):
    value : bpy.props.IntVectorProperty(size=2)

class ClothCrossConstraint(bpy.types.PropertyGroup):
    value : bpy.props.IntVectorProperty(size=2)

class ClothBendConstraint(bpy.types.PropertyGroup):
    value : bpy.props.IntVectorProperty(size=2)

class ClothCollisionProp(bpy.types.PropertyGroup):
    ob : bpy.props.PointerProperty(type=bpy.types.Object)
    ob_type : bpy.props.EnumProperty(items=[
        ('sphere','Sphere','Sphere',0),
        ('sphere2', 'Sphere2', 'Sphere2', 1),
        ('cylinder', 'Cylinder', 'Cylinder', 2),
        ('cube', 'Cube', 'Cube', 4)
    ])
    x : bpy.props.FloatProperty(name='X', default=1.0)
    y : bpy.props.FloatProperty(name='Y', default=1.0)
    z : bpy.props.FloatProperty(name='Z', default=1.0)



cloth_props = [ClothFixedPointProp,
ClothStretchConstraint,
ClothCrossConstraint,
ClothBendConstraint,
ClothCollisionProp]

class ClothOpSetFixedPoints(bpy.types.Operator):
    bl_label = 'Set fixed points for Cloth'
    bl_idname = 'mesh.ze_clth_op_fixed_add'
    bl_options = {'REGISTER','UNDO'}

    @classmethod
    def poll(cls, context):
        return context.object.type == 'MESH' and context.object.mode == 'EDIT'

    def execute(self, context):
        print('letting me know something at least')
        bpy.ops.mesh.ze_clth_op_fixed_clear()
        verts = context.object.data.vertices
        bpy.ops.object.mode_set(mode='OBJECT')
        for v in verts:
            if(v.select == True):
                point = context.object.ze_cloth_fixed_points.add()
                point.value = v.index
        bpy.ops.object.mode_set(mode='EDIT')
        return {'FINISHED'}

class ClothOpSelectFixedPoints(bpy.types.Operator):
    bl_label = 'Select fixed points for Cloth'
    bl_idname = 'mesh.ze_clth_op_fixed_select'
    bl_options = {'REGISTER','UNDO'}

    @classmethod
    def poll(cls, context):
        return context.object.type == 'MESH' and context.object.mode == 'EDIT'

    def execute(self, context):
        ob = context.object
        bpy.ops.object.mode_set(mode='OBJECT')
        for fdx in ob.ze_cloth_fixed_points:
            ob.data.vertices[fdx.value].select = True
        bpy.ops.object.mode_set(mode='EDIT')

        return {'FINISHED'}

class ClothOpClearFixedPoints(bpy.types.Operator):
    bl_label = 'Clear fixed points for Cloth'
    bl_idname = 'mesh.ze_clth_op_fixed_clear'
    bl_options = {'REGISTER','UNDO'}

    @classmethod
    def poll(cls, context):
        return context.object.type == 'MESH'

    def execute(self, context):
        ob = context.object
        ob.ze_cloth_fixed_points.clear()
        return {'FINISHED'}

# ##
class ClothOpSetStretchConstraints(bpy.types.Operator):
    bl_label = 'Assign Stretch Constraints for Cloth'
    bl_idname = 'mesh.ze_clth_op_stretch_assign'
    bl_options = {'REGISTER','UNDO'}

    @classmethod
    def poll(cls, context):
        return context.object.type == 'MESH' and context.object.mode == 'EDIT'

    def execute(self, context):
        ob = bpy.context.object
        bpy.ops.mesh.ze_clth_op_stretch_clear()
        bpy.ops.object.mode_set(mode='OBJECT')
        for ej in ob.data.edges:
            if(ej.select):
                cst = ob.ze_cloth_stretch_constraints.add()
                cst.value = ej.vertices[:]
        bpy.ops.object.mode_set(mode='EDIT')
        return {'FINISHED'}

class ClothOpSelectStretchConstraints(bpy.types.Operator):
    bl_label = 'Select stretch constraints for cloth'
    bl_idname = 'mesh.ze_clth_op_stretch_select'
    bl_options = {'REGISTER','UNDO'}

    @classmethod
    def poll(cls, context):
        return context.object.type == 'MESH' and context.object.mode == 'EDIT'

    def execute(self, context):
        ob = context.object
        edge = None
        bpy.ops.object.mode_set(mode='OBJECT')
        for stretch in ob.ze_cloth_stretch_constraints:
            edge_list = [e for e in ob.data.edges]
            for i in stretch.value:
                edge_list = [e for e in edge_list if i in e.vertices]

            if(len(edge_list)==1):
                edge = edge_list[-1]
                edge.select = True
        bpy.ops.object.mode_set(mode='EDIT')

        return {'FINISHED'}

class ClothOpClearStretchConstraints(bpy.types.Operator):
    bl_label = 'Clear Stretch Constraints for Cloth'
    bl_idname = 'mesh.ze_clth_op_stretch_clear'
    bl_options = {'REGISTER','UNDO'}

    @classmethod
    def poll(cls, context):
        return context.object.type == 'MESH'

    def execute(self, context):
        ob = context.object
        ob.ze_cloth_stretch_constraints.clear()
        return {'FINISHED'}

class ClothOpSetCrossConstraints(bpy.types.Operator):
    bl_label = 'Assign Cross Constraint for Cloth'
    bl_idname = 'mesh.ze_clth_op_cross_assign'
    bl_options = {'REGISTER','UNDO'}

    @classmethod
    def poll(cls, context):
        return context.object.type == 'MESH' and context.object.mode == 'EDIT'

    def execute(self, context):
        ob = context.object

        bpy.ops.mesh.ze_clth_op_cross_clear()

        bpy.ops.object.mode_set(mode='OBJECT')

        edge_list = [e.vertices[:] for e in ob.data.edges if e.select == True]
        for edge in edge_list:
            cross = ob.ze_cloth_cross_constraints.add()
            cross.value = edge

            tris = [t.vertices for t in ob.data.polygons]
            for idx in edge:
                tris = [t for t in tris if idx in t]

            edge2 = []
            for t in tris:
                assert len(t) == 3, 'Must be triangles'
                for tidx in t:
                    if tidx not in edge:
                        edge2.append(tidx)
            edge2 = tuple(edge2)
            cross2 = ob.ze_cloth_cross_constraints.add()
            cross2.value = edge2

        bpy.ops.object.mode_set(mode='EDIT')

        return {'FINISHED'}

class ClothOpSelectCrossConstraints(bpy.types.Operator):
    bl_label = 'Select cross constraints for cloth'
    bl_idname = 'mesh.ze_clth_op_cross_select'
    bl_options = {'REGISTER','UNDO'}
    
    @classmethod
    def poll(cls, context):
        return context.object.type == 'MESH' and context.object.mode == 'EDIT'

    def execute(self, context):
        ob = context.object
        edge = None
        bpy.ops.object.mode_set(mode='OBJECT')
        for cross in ob.ze_cloth_cross_constraints:
            edge_list = [e for e in ob.data.edges]
            for i in cross.value:
                edge_list = [e for e in edge_list if i in e.vertices]

            if(len(edge_list)==1):
                edge = edge_list[-1]
                edge.select = True
        bpy.ops.object.mode_set(mode='EDIT')
        return {'FINISHED'}

class ClothOpClearCrossConstraints(bpy.types.Operator):
    bl_label = 'Clear Cross Constraints for Cloth'
    bl_idname = 'mesh.ze_clth_op_cross_clear'
    bl_options = {'REGISTER','UNDO'}

    @classmethod
    def poll(cls, context):
        return context.object.type == 'MESH'

    def execute(self, context):
        ob = context.object
        ob.ze_cloth_cross_constraints.clear()
        return {'FINISHED'}

class ClothOpSetBendConstraints(bpy.types.Operator):
    bl_label = 'Assign Bend Constraints for Cloth'
    bl_idname = 'mesh.ze_clth_op_bend_assign'
    bl_options = {'REGISTER','UNDO'}

    @classmethod
    def poll(cls, context):
        return context.object.type == 'MESH' and context.object.mode == 'EDIT'

    def execute(self, context):
        ob = bpy.context.object
        bpy.ops.mesh.ze_clth_op_bend_clear()
        bpy.ops.object.mode_set(mode='OBJECT')
        for ej in ob.data.edges:
            if(ej.select):
                cst = ob.ze_cloth_bend_constraints.add()
                cst.value = ej.vertices[:]
        bpy.ops.object.mode_set(mode='EDIT')
        return {'FINISHED'}

class ClothOpSelectBendConstraints(bpy.types.Operator):
    bl_label = 'Select bend constraints for cloth'
    bl_idname = 'mesh.ze_clth_op_bend_select'
    bl_options = {'REGISTER','UNDO'}

    @classmethod
    def poll(cls, context):
        return context.object.type == 'MESH' and context.object.mode == 'EDIT'

    def execute(self, context):
        ob = context.object

        if(ob.ze_object.clth_bend_cage):
            return {'CANCELLED'}

        ob.ze_object.clth_before_cage_index = len(ob.data.edges)

        edge = None
        bpy.ops.object.mode_set(mode='OBJECT')
        for bend in ob.ze_cloth_bend_constraints:
            edge = ob.data.edges.add(1)
            ob.data.edges[-1].vertices = bend.value
        ob.data.update()

        bpy.ops.object.mode_set(mode='EDIT')

        ob.ze_object.clth_bend_cage = True
        return {'FINISHED'}

class ClothOpSelectBendConstraints_FS(bpy.types.Operator):
    bl_label = 'Select bend constraints for cloth'
    bl_idname = 'mesh.ze_clth_op_bend_select_fs'
    bl_options = {'REGISTER','UNDO'}

    @classmethod
    def poll(cls, context):
        return context.object.type == 'MESH' and context.object.mode == 'EDIT'

    def execute(self, context):
        ob = context.object

        if(ob.ze_object.clth_bend_cage == True):
            return {'CANCELLED'}

        ob.ze_object.clth_before_cage_index = len(ob.data.edges)

        bpy.ops.object.mode_set(mode='OBJECT')
        vert_list = []
        edge_list = []
        for vert in ob.data.vertices:
            if(vert.select):
                vert_list.append(vert.index)

        master_edge_list = [e.vertices[:] for e in ob.data.edges]
        for x in vert_list:
            for y in vert_list:
                if(x != y):
                    if((x, y) not in master_edge_list\
                        and (y, x) not in master_edge_list\
                        and (y, x) not in edge_list):
                        ej = (x, y)
                        edge_list.append(ej)


        for edge in edge_list:
            ob.data.edges.add(1)
            ob.data.edges[-1].vertices = edge
        ob.data.update()

        bpy.ops.object.mode_set(mode='EDIT')


        ob.ze_object.clth_bend_cage = True
        return {'FINISHED'}

class ClothOpClearBendConstraints(bpy.types.Operator):
    bl_label = 'Clear Bend Constraints for Cloth'
    bl_idname = 'mesh.ze_clth_op_bend_clear'
    bl_options = {'REGISTER','UNDO'}

    @classmethod
    def poll(cls, context):
        return context.object.type == 'MESH'

    def execute(self, context):
        ob = context.object
        ob.ze_cloth_bend_constraints.clear()
        return {'FINISHED'}

class ClothOpSelectCage(bpy.types.Operator):
    bl_label = 'Select Cage'
    bl_idname = 'mesh.ze_clth_cage_select'
    bl_options = {'REGISTER','UNDO'}

    @classmethod
    def poll(cls, context):
        return context.object.type == 'MESH' and context.object.mode == 'EDIT'

    def execute(self, context):
        ob = context.object
        if(ob.ze_object.clth_bend_cage == False):
            return {'CANCELLED'}

        bpy.ops.object.mode_set(mode='OBJECT')
        start = ob.ze_object.clth_before_cage_index
        num_edges = len(ob.data.edges)
        for i in range(start, num_edges):
            ob.data.edges[i].select = True
        bpy.ops.object.mode_set(mode='EDIT')
        
        return {'FINISHED'}

class ClothOpRemoveCage(bpy.types.Operator):
    bl_label = 'Remove Cage'
    bl_idname = 'mesh.ze_clth_cage_remove'
    bl_options = {'REGISTER','UNDO'}

    @classmethod
    def poll(cls, context):
        return context.object.type == 'MESH' and context.object.mode == 'EDIT' and\
            bpy.context.tool_settings.mesh_select_mode[1] == True \
            and bpy.context.tool_settings.mesh_select_mode[0] == False \
            and bpy.context.tool_settings.mesh_select_mode[2] == False

    def execute(self, context):
        ob = context.object
        if(ob.ze_object.clth_bend_cage == False):
            return {'CANCELLED'}

        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT')
        start = ob.ze_object.clth_before_cage_index
        num_edges = len(ob.data.edges)
        for i in range(start, num_edges):
            ob.data.edges[i].select = True
        bpy.ops.object.mode_set(mode='EDIT')
        
        bpy.ops.mesh.delete(type='EDGE_FACE')
        ob.ze_object.clth_bend_cage = False

        #refresh object's data so we have no left over deleted edge data
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.mode_set(mode='EDIT')
        
        return {'FINISHED'}

class ClothOpCollisionAdd(bpy.types.Operator):
    bl_label = 'Add Cloth Collision Object'
    bl_idname = 'mesh.ze_clth_collision_add'
    bl_options = {'REGISTER','UNDO'}

    def execute(self, context):
        ob = context.object
        ob.ze_cloth_collision_objects.add()
        return {'FINISHED'}  

class ClothOpCollisionRemove(bpy.types.Operator):
    bl_label = 'Remove Cloth Collision Object'
    bl_idname = 'mesh.ze_clth_collision_remove'
    bl_options = {'REGISTER','UNDO'}

    def execute(self, context):
        ob = context.object
        ob.ze_cloth_collision_objects.remove(0)
        return {'FINISHED'}  


cloth_ops = [ClothOpSetFixedPoints,
ClothOpSelectFixedPoints,
ClothOpClearFixedPoints,

ClothOpSetStretchConstraints,
ClothOpSelectStretchConstraints,
ClothOpClearStretchConstraints,

ClothOpSetCrossConstraints,
ClothOpSelectCrossConstraints,
ClothOpClearCrossConstraints,

ClothOpSetBendConstraints,
ClothOpSelectBendConstraints,
ClothOpSelectBendConstraints_FS,
ClothOpClearBendConstraints,
ClothOpSelectCage,
ClothOpRemoveCage,

ClothOpCollisionAdd,
ClothOpCollisionRemove]

class ZeroEngineOpDummy(bpy.types.Operator):
    bl_idname = 'object.zerodummy'
    bl_label = 'Dummy Operator'

    def execute(self, context):
        print('Dummy Op')
        return {'FINISHED'}

class ZeroEngineObjectData(bpy.types.PropertyGroup):
    #object type
    object_index : bpy.props.IntProperty(name='Object Index', subtype='UNSIGNED')
    object_type : bpy.props.EnumProperty(name='Object Type', 
    items=[
    ('null', 'Null', 'An absolute null object'),
    ('geodynamic', 'Dynamic', 'A mesh object that contains envelopes and constrains'),
    ('cloth', 'Cloth', 'Obviously Cloth'),
    ('bone', 'Bone', 'An animated Null'),
    ('geobone', 'Animated', 'a non-enveloped animated mesh'),
    ('staticgeo', 'Static Geometry', 'Plain Geometry'),
    ('shadowgeo', 'Shadow Geometry', 'Shadow'),
    ])
    #object flags (i.e. hidden or visible)
    collision : bpy.props.BoolProperty(name='Collision', default=0)
    hidden : bpy.props.BoolProperty(name='Hidden', default=0)

    chain_object : bpy.props.BoolProperty(name='Chain Object', default = False)
    constraint : bpy.props.FloatProperty(name='Bone Constraint', default=1.0, min=-1.0, max=1.0)
    blend_factor : bpy.props.FloatProperty(name='Blend Factor', default=0.0, min=0.0, max = 1.0)

    clth_texture : bpy.props.PointerProperty(name = 'Texture', type =bpy.types.Image)
    clth_bend_cage : bpy.props.BoolProperty(name='has_cage?', default=False)
    clth_before_cage_index : bpy.props.IntProperty(name='num_of_edges_before_cage', default=0)

    collision_type : bpy.props.EnumProperty(name='Type', 
    items=[('sphere','Sphere','Sphere', 0),
    ('sphere2', 'Sphere 2', 'Sphere 2', 1),
    ('cylinder', 'Cylinder', 'Cylinder', 2),
    ('cube','Cube','Cube', 4),
    ])
    collision_x : bpy.props.FloatProperty(name='X', default=1.0)
    collision_y : bpy.props.FloatProperty(name='Y', default=1.0)
    collision_z : bpy.props.FloatProperty(name='Z', default=1.0)

class ZeroEngineMaterialData(bpy.types.PropertyGroup):
    #index
    index : bpy.props.IntProperty(name='Index', default=0, description='index for keeping track of materials')
    
    #diffuse
        #normalized rgba 0.0 - 1.0
    diffuse : bpy.props.FloatVectorProperty(name='Diffuse',
    description='sets the surface color for engine object',
    size=4,
    default=(0.8,0.8,0.8,1.0),
    subtype='COLOR',
    min=0.0,
    max=1.0,
    )
    #specular
    specular : bpy.props.FloatVectorProperty(name='Specular',
    description='sets the specular color for engine object',
    size=4,
    default=(0.8,0.8,0.8,1.0),
    subtype='COLOR',
    min=0.0,
    max=1.0,
    )
    #ambient
    ambient : bpy.props.FloatVectorProperty(name='Ambient',
    description='sets the ambient color for engine object',
    size=4,
    default=(0.8,0.8,0.8,1.0),
    subtype='COLOR',
    min=0.0,
    max=1.0,
    )
    #specular intensity
    specular_sharpness : bpy.props.FloatProperty(
        name='Specular Sharpness',
        description='Defines the glossiness of the material',
        default = 0.0,
        min=0.0,
        max=1.0
    )
    #render attributes
    flags : bpy.props.EnumProperty(name='Flags', options={'ENUM_FLAG'},
    items=[
        ('emissive', 'Emissive', 'test'),
        ('glow', 'Glow', 'test'),
        ('single', '1-Side Transparency', 'test'),
        ('double', '2-Side Transparency', 'test'),
        ('hard', 'Hard Transparency', 'test'),
        ('ppl', 'PerPixel', 'test'),
        ('add', 'Additive', 'test'),
        ('spec', 'Specular', 'test')
    ])

    render_type : bpy.props.EnumProperty(name='Render Type', 
    items=[
    ('normal', 'Normal', 'for test purposes'),
    ('glow', 'Glow', 'for test purposes'),
    ('light_map', 'Light Map', 'for test purposes'),
    ('scrolling', 'Scrolling', 'for test purposes'),
    ('specular', 'Specular', 'for test purposes'),
    ('gloss_map', 'Gloss Map', 'for test purposes'),
    ('chrome', 'Chrome', 'for test purposes'),
    ('animated', 'Animated', 'for test purposes'),
    ('ice', 'Ice', 'for test purposes'),
    ('sky', 'Sky', 'for test purposes'),
    ('water', 'Water', 'for test purposes'),
    ('detail', 'Detail', 'for test purposes'),
    ('two_scroll', '2 Scroll', 'for test purposes'),
    ('rotate', 'Rotate', 'for test purposes'),
    ('glow_rotate', 'Glow Rotate', 'for test purposes'),
    ('planar_reflection', 'Planar Reflection', 'for test purposes'),
    ('glow_scroll', 'Glow Scroll', 'for test purposes'),
    ('glow_2_scroll', 'Glow 2 Scroll', 'for test purposes'),
    ('curved_reflection', 'Curved Reflection', 'for test purposes'),
    ('normal_map_fade', 'Normal Map Fade', 'for test purposes'),
    ('normal_map_inv_fade', 'Normal Map Inv Fade', 'for test purposes'),
    ('ice_reflection', 'Ice Reflection', 'for test purposes'),
    ('ice_refraction', 'Ice Refraction', 'for test purposes'),
    ('emboss', 'Emboss', 'for test purposes'),
    ('wire_frame', 'Wireframe', 'for test purposes'),
    ('energy', 'Energy', 'for test purposes'),
    ('after_burner', 'After Burner', 'for test purposes'),
    ('bump_map', 'Bump Map', 'for test purposes'),
    ('bump_gloss_map', 'Bump Gloss Map', 'for test purposes'),
    ('teleportal', 'Teleportal', 'for test purposes'),
    ('multistate', 'Multistate', 'for test purposes'),
    ('shield', 'Shield', 'for test purposes'),
    ])

    # 0 - 255 value data inputs
    data1 : bpy.props.IntProperty(
        name='Data1',
        default=0,
        subtype='UNSIGNED',
        min=0,
        max=255)

    data2 : bpy.props.IntProperty(
        name='Data2',
        default=0,
        subtype='UNSIGNED',
        min=0,
        max=255)

    texture1 : bpy.props.PointerProperty(name='Texture 1', type=bpy.types.Image)
    texture2 : bpy.props.PointerProperty(name='Texture 2', type=bpy.types.Image)
    texture3 : bpy.props.PointerProperty(name='Texture 3', type=bpy.types.Image)
    texture4 : bpy.props.PointerProperty(name='Texture 4', type=bpy.types.Image)
    #texture

class ZeroEngineObjectDataPanel(bpy.types.Panel):
    bl_idname = 'ZE_OBJECT_PT_settings'
    bl_label = 'ZE Object Settings'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'object'

    def draw(self, context):
        layout = self.layout

        obj = context.object.ze_object
        cloth = context.object

        col = layout.column()
        col.prop(obj, 'object_index')
        col.prop(obj, 'object_type')
        row = col.row()
        row.prop(obj, 'collision')
        row.prop(obj, 'hidden')
        if(obj.collision):
            box = col.box()
            box.prop(obj, 'collision_type')
            box.prop(obj, 'collision_x')
            box.prop(obj, 'collision_y')
            box.prop(obj, 'collision_z')

        if(obj.object_type == 'cloth'):
            col.label(text='Cloth Settings:')
            box = col.box()

            box.prop(obj, 'clth_texture')

            box.label(text = 'Fixed Points:')
            row = box.row()
            row.operator(ClothOpSetFixedPoints.bl_idname, text='Assign')
            row.operator(ClothOpSelectFixedPoints.bl_idname, text='Select')
            row.operator(ClothOpClearFixedPoints.bl_idname, text='Delete')
            if(len(cloth.ze_cloth_fixed_points)==0):
               temp_row = box.row()
               temp_row.alignment = 'CENTER'
               temp_row.label(text='nothing assigned')
            else:
                temp_row = box.row()
                temp_row.alignment = 'CENTER'
                temp_row.label(text='Count: {}'.format(len(cloth.ze_cloth_fixed_points)))
            
            box.label(text = 'Stretch Constraints:')
            row = box.row()
            row.operator(ClothOpSetStretchConstraints.bl_idname, text='Assign')
            row.operator(ClothOpSelectStretchConstraints.bl_idname, text='Select')
            row.operator(ClothOpClearStretchConstraints.bl_idname, text='Delete')
            if(len(cloth.ze_cloth_stretch_constraints)==0):
               temp_row = box.row()
               temp_row.alignment = 'CENTER'
               temp_row.label(text='nothing assigned')
            else:
                temp_row = box.row()
                temp_row.alignment = 'CENTER'
                temp_row.label(text='Count: {}'.format(len(cloth.ze_cloth_stretch_constraints)))
            
            box.label(text = 'Cross Constraints:')
            row = box.row()
            row.operator(ClothOpSetCrossConstraints.bl_idname, text='Assign')
            row.operator(ClothOpSelectCrossConstraints.bl_idname, text='Select')
            row.operator(ClothOpClearCrossConstraints.bl_idname, text='Delete')
            if(len(cloth.ze_cloth_cross_constraints)==0):
               temp_row = box.row()
               temp_row.alignment = 'CENTER'
               temp_row.label(text='nothing assigned')
            else:
                temp_row = box.row()
                temp_row.alignment = 'CENTER'
                temp_row.label(text='Count: {}'.format(len(cloth.ze_cloth_cross_constraints)))

            box.label(text = 'Bend Constraints:')
            row = box.row()
            row.operator(ClothOpSetBendConstraints.bl_idname, text='Assign')
            row.operator(ClothOpClearBendConstraints.bl_idname, text='Delete')
            if(cloth.ze_object.clth_bend_cage == False):    
                row = box.row()
                row.operator(ClothOpSelectBendConstraints_FS.bl_idname, text='Create Cage (Selection)')
                row.operator(ClothOpSelectBendConstraints.bl_idname, text='Create Cage')
            else:
                row = box.row()
                row.operator(ClothOpSelectCage.bl_idname, text='Select Cage')
                row.operator(ClothOpRemoveCage.bl_idname, text='Remove Cage')
            box.row().label(text='dbg_clth: {}'.format(cloth.ze_object.clth_before_cage_index))

            if(len(cloth.ze_cloth_bend_constraints)==0):
               temp_row = box.row()
               temp_row.alignment = 'CENTER'
               temp_row.label(text='nothing assigned')
            else:
                temp_row = box.row()
                temp_row.alignment = 'CENTER'
                temp_row.label(text='Count: {}'.format(len(cloth.ze_cloth_bend_constraints)))

            box.label(text = 'Collisions:')
            row = box.row()
            row.operator(ClothOpCollisionAdd.bl_idname, text='Add')
            row.operator(ClothOpCollisionRemove.bl_idname, text='Delete')
            temp_row = box.row()
            temp_row.alignment = 'CENTER'
            if(len(cloth.ze_cloth_collision_objects) < 1):
                temp_row.label(text='nothing assigned')
            else:
                temp_row.label(text='count: {}'.format(len(cloth.ze_cloth_collision_objects)))
                for col in cloth.ze_cloth_collision_objects:
                    box.prop(col, 'ob')
                    box.prop(col, 'ob_type')
                    box.prop(col, 'x')
                    box.prop(col, 'y')
                    box.prop(col, 'z')
                    box.separator()


        if(obj.object_type == 'bone' or obj.object_type == 'null'):
            col.label(text='Skeleton Settings:')
            box = col.box()
            box.prop(obj, 'chain_object')
            box.prop(obj, 'constraint')
            box.prop(obj, 'blend_factor')


class ZeroEngineMaterialDataPanel(bpy.types.Panel):
    bl_idname = 'ZE_MATERIAL_PT_settings'
    bl_label = 'ZE Material Settings'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'material'

    def draw(self, context):
        layout = self.layout

        mat = context.material.ze_material

        col = layout.column()
        #row = layout.row()
        col.prop(mat, 'index')
        col.prop(mat, 'diffuse')
        #row = layout.row()
        col.prop(mat, 'specular')
        #row = layout.row()
        col.prop(mat, 'ambient')
        #row = layout.row()
        col.prop(mat, 'specular_sharpness')
        #row = layout.row()
        col.separator(factor=4.0)
        col.label(text='Render Settings:')
        box = col.box()
        box.label(text='Flags:')
        grid = box.grid_flow(row_major=True, columns=2)
        grid.prop(mat, 'flags')
        col.prop(mat, 'render_type')
        col.prop(mat, 'data1')
        col.prop(mat, 'data2')
        col.prop(mat, 'texture1')
        col.prop(mat, 'texture2') 
        col.prop(mat, 'texture3')
        col.prop(mat, 'texture4')


def my_import_menu_func(self, context):
    self.layout.operator(import_zero.ImportZero.bl_idname)
def my_export_menu_func(self, context):
    self.layout.operator(export_zero.ExportZero.bl_idname)

def register():
    #register properties

    for prop in cloth_props:
        bpy.utils.register_class(prop)

    for op in cloth_ops:
        bpy.utils.register_class(op)

    bpy.utils.register_class(ZeroEngineObjectData)
    bpy.utils.register_class(ZeroEngineMaterialData)

    bpy.types.Object.ze_object = bpy.props.PointerProperty(type=ZeroEngineObjectData)
    bpy.types.Object.ze_cloth_fixed_points = bpy.props.CollectionProperty(type=ClothFixedPointProp)
    bpy.types.Object.ze_cloth_stretch_constraints = bpy.props.CollectionProperty(type=ClothStretchConstraint)
    bpy.types.Object.ze_cloth_cross_constraints = bpy.props.CollectionProperty(type=ClothCrossConstraint)
    bpy.types.Object.ze_cloth_bend_constraints = bpy.props.CollectionProperty(type=ClothBendConstraint)
    bpy.types.Object.ze_cloth_collision_objects = bpy.props.CollectionProperty(type=ClothCollisionProp)

    bpy.types.Material.ze_material = bpy.props.PointerProperty(type=ZeroEngineMaterialData)
    #register panels
    bpy.utils.register_class(ZeroEngineObjectDataPanel)
    bpy.utils.register_class(ZeroEngineMaterialDataPanel)
    #register import/export/ops
    bpy.utils.register_class(import_zero.ImportZero)
    bpy.utils.register_class(export_zero.ExportZero)

    bpy.utils.register_class(ZeroEngineOpDummy)

    bpy.types.TOPBAR_MT_file_import.append(my_import_menu_func)
    bpy.types.TOPBAR_MT_file_export.append(my_export_menu_func)

    for item in tool_ops:
        bpy.utils.register_class(item)
    bpy.types.VIEW3D_MT_object_context_menu.append(draw_zero_menu)
    bpy.types.VIEW3D_MT_pose_context_menu.append(draw_zero_menu)

def unregister():
    #unregister import/export/ops
    bpy.types.TOPBAR_MT_file_import.remove(my_import_menu_func)
    bpy.types.TOPBAR_MT_file_export.remove(my_export_menu_func)

    bpy.utils.unregister_class(ZeroEngineOpDummy)

    bpy.utils.unregister_class(import_zero.ImportZero)
    bpy.utils.unregister_class(export_zero.ExportZero)
    #unregister panels
    bpy.utils.unregister_class(ZeroEngineObjectDataPanel)
    bpy.utils.unregister_class(ZeroEngineMaterialDataPanel)
    #unregister properties
    del bpy.types.Material.ze_material
    del bpy.types.Object.ze_object

    del bpy.types.Object.ze_cloth_fixed_points
    del bpy.types.Object.ze_cloth_stretch_constraints
    del bpy.types.Object.ze_cloth_cross_constraints
    del bpy.types.Object.ze_cloth_bend_constraints
    del bpy.types.Object.ze_cloth_collision_objects


    bpy.utils.unregister_class(ZeroEngineObjectData)
    bpy.utils.unregister_class(ZeroEngineMaterialData)

    for op in cloth_ops:
        bpy.utils.unregister_class(op)

    for prop in cloth_props:
        bpy.utils.unregister_class(prop)

    bpy.types.VIEW3D_MT_object_context_menu.remove(draw_zero_menu)
    bpy.types.VIEW3D_MT_pose_context_menu.remove(draw_zero_menu)

    for item in tool_ops:
        bpy.utils.unregister_class(item)