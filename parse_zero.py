import sys
import io
import struct

from . import msh2_crc

zero_id_dict = {
    'HEDR':(lambda file, chunk: read_subchunks(file, chunk),
    None),
    'MSH2':(lambda file, chunk: read_subchunks(file, chunk),
    None),
    'SINF':(lambda file, chunk: read_subchunks(file, chunk),
    None),

    'NAME':(lambda file, chunk: update_chunk_dict(chunk, data=zero_string(file, chunk)),
    {'data':'{0}s{1}x'}),
    'FRAM':(lambda file, chunk: update_chunk_dict(chunk, start_frame = u32(file),
    end_frame = u32(file), frame_rate = sf32(file)),
    {'start':'I','end':'I','rate':'f'}),

    'BBOX':(lambda file, chunk: skip_chunk(file, chunk),
    None),

    'MATL':(lambda file, chunk: read_indexed_subchunks(file, chunk, u32(file)),
    {'data':'I'}),

    'MATD':(lambda file, chunk: read_subchunks(file, chunk),
    None),

    'DATA':(lambda file, chunk: update_chunk_dict(chunk, diffuse=data_seq(file, 4, 'f', 0, chunk),
    ambient=data_seq(file, 4, 'f', 0, chunk), specular_color=data_seq(file, 4, 'f', 0, chunk), specular_strength=sf32(file)) if \
        chunk.parent.name == 'MATD' else skip_chunk(file,chunk),
        {'diffuse':'4f', 'ambient':'4f', 'specular':'4f', 'specular_strength':'f'}),

    'ATRB':(lambda file, chunk: update_chunk_dict(chunk, flags=u8(file), render_type=u8(file), data0=u8(file), data1=u8(file)),
    {'flags':'B', 'render_type':'B', 'data0':'B', 'data1':'B'}),
    
    'TX0D':(lambda file, chunk: update_chunk_dict(chunk, data=zero_string(file, chunk)),
    {'data':'{0}s{1}x'}),
    'TX1D':(lambda file, chunk: update_chunk_dict(chunk, data=zero_string(file, chunk)),
    None),
    'TX2D':(lambda file, chunk: update_chunk_dict(chunk, data=zero_string(file, chunk)),
    None),
    'TX3D':(lambda file, chunk: update_chunk_dict(chunk, data=zero_string(file, chunk)),
    None),

    'MODL':(lambda file, chunk: read_subchunks(file, chunk),
    None),
    'MTYP':(lambda file, chunk: update_chunk_dict(chunk, model_type=u32(file)),
    {'data':'I'}),
    'MNDX':(lambda file, chunk: update_chunk_dict(chunk, model_index=u32(file)),
    {'data':'I'}),
    'FLGS':(lambda file, chunk: update_chunk_dict(chunk, flags=u32(file)),
    {'data':'I'}),

    'TRAN':(lambda file, chunk: update_chunk_dict(chunk, scale=data_seq(file, 3, 'f', 0, chunk),
     quaternion=data_seq(file, 4, 'f', 0, chunk), location=data_seq(file, 3, 'f', 0, chunk)),
     {'scale':'3f', 'rotation':'4f', 'location':'3f'}),

    'SWCI':(lambda file, chunk: update_chunk_dict(chunk, coll_type=u32(file), x=sf32(file),y=sf32(file),z=sf32(file)),
    {'type':'I', 'x':'f', 'y':'f', 'z':'f'}),

    'PRNT':(lambda file, chunk: update_chunk_dict(chunk, data=zero_string(file, chunk)),
    {'data':'{0}s{1}x'}),
    'GEOM':(lambda file, chunk: read_subchunks(file, chunk),
    None),
    'BBOX':(lambda file, chunk: skip_chunk(file, chunk),
    {'rotation':'4f', 'center':'3f', 'extents':'3f', 'radius':'f'}),
    'SEGM':(lambda file, chunk: read_subchunks(file, chunk),
    None),
    'MATI':(lambda file, chunk: update_chunk_dict(chunk, material_index=u32(file)),
    {'data':'I'}),
    
    'POSL':(lambda file, chunk: update_chunk_dict(chunk, verts=data_seq(
        file, 3, 'f', u32(file), chunk)),
        {'count':'I', 'data':'3f'}),


    'WGHT':(lambda file, chunk: update_chunk_dict(chunk,
        weights=read_weights(file)),
        {'count':'I','data':'If'}),

    'NRML':(lambda file, chunk: skip_chunk(file, chunk),
    {'count':'I','data':'3f'}),
    
    'UV0L':(lambda file, chunk: update_chunk_dict(chunk, uvs=data_seq(
    file, 2, 'f', u32(file), chunk)),
    {'count':'I', 'data':'2f'}),

    'NDXL':(lambda file, chunk: skip_chunk(file, chunk),
    None),
    'NDXT':(lambda file, chunk: update_chunk_dict(chunk, tris=data_seq(
    file, 3, 'H', u32(file), chunk)),
    {'count':'I', 'data':'3H'}),

    'STRP':(lambda file, chunk: skip_chunk(file, chunk),
    {'count':'I','data':None}),
    'ENVL':(lambda file, chunk: update_chunk_dict(chunk, envelopes=data_seq(
    file, 1, 'I', u32(file), chunk)),
    {'count':'I', 'data':'I'}),

    'SHDW':(lambda file, chunk: read_shadow_mesh(file, chunk),
    {'num_verts':'I', 'verts':'3f', 'num_edges':'I', 'edges':'4H'}),

    'CLTH':(lambda file, chunk: read_subchunks(file, chunk),
    None),
    'CTEX':(lambda file, chunk: update_chunk_dict(chunk, data=zero_string(file, chunk)),
    {'data':'{}s{}x'}),
    'CPOS':(lambda file, chunk: update_chunk_dict(chunk, cloth_verts=data_seq(file, 3, 'f', u32(file), chunk)),
    {'count':'I', 'data':'3f'}),
    'CUV0':(lambda file, chunk: update_chunk_dict(chunk, cloth_uvs=data_seq(file, 2, 'f', u32(file), chunk)),
    {'count':'I', 'data':'2f'}),
    'FIDX':(lambda file, chunk: update_chunk_dict(chunk, fixed_points=data_seq(file, 1, 'I', u32(file), chunk)),
    {'count':'I', 'data':'I'}),
    'FWGT':(lambda file, chunk: read_cloth_weights(file, chunk),
    {'data':None}), #bytes object
    'CMSH':(lambda file, chunk: update_chunk_dict(chunk, cloth_tris=data_seq(file, 3, 'I', u32(file), chunk)),
    {'count':'I', 'data':'3I'}),
    'SPRS':(lambda file, chunk: update_chunk_dict(chunk, stretch_constraints=data_seq(file, 2, 'H', u32(file), chunk)),
    {'count':'I', 'data':'2H'}),
    'CPRS':(lambda file, chunk: update_chunk_dict(chunk, cross_constraints=data_seq(file, 2, 'H', u32(file), chunk)),
    {'count':'I', 'data':'2H'}),
    'BPRS':(lambda file, chunk: update_chunk_dict(chunk, bend_constraints=data_seq(file, 2, 'H', u32(file), chunk)),
    {'count':'I', 'data':'2H'}),
    'COLL':(lambda file, chunk: read_cloth_collisions(file, chunk),
    {'data':None}), #data is a bytes object it is written directly to the file.
    'SKL2':(lambda file, chunk: read_zero_skeleton(file, chunk),
    {'count':'I', 'data':'2I3f'}),
    'BLN2':(lambda file, chunk: read_zero_blend_factors(file, chunk),
    {'count':'I', 'data':'If'}),
    'ANM2':(lambda file, chunk: read_subchunks(file, chunk),
    None),
    'CYCL':(lambda file, chunk: update_chunk_dict(chunk,
     animations = read_animation_cycle_data(file)),
     {'count':'I', 'ani_name':'13s51x', 'frame_rate':'f', 'play_style':'I', 'first_frame':'I', 'last_frame':'I'}),

    'KFR3':(lambda file, chunk: update_chunk_dict(chunk, 
    keyframes = read_keyframes_per_bone(file, chunk)),
    {'count':'I', 'data':None}),

    'CL1L':(lambda file, chunk: skip_chunk(file, chunk),
    None),
}
def u8(file):
    return struct.unpack('<B', file.read(1))[0]

def u16(file):
    return struct.unpack('<H', file.read(2))[0]

def u32(file):
    return struct.unpack('<I', file.read(4))[0]

def zero_string(file, chunk, ascii=False):
    if(ascii):
        if 'bytes_read' not in chunk.__dict__.keys():
            chunk.bytes_read = 0
        temp = b''
        c = b''
        while(True):
            c = file.read(1)
            chunk.bytes_read += 1
            if(c == b'\x00'):
                break
            temp += c
        return temp.decode('utf-8')

    else:
        size = chunk.size_in_bytes
        data = struct.unpack('{0}s'.format(size), file.read(size))[0]
        return data.decode('utf-8').rstrip('\x00')

def sf32(file):
    return struct.unpack('<f', file.read(4))[0]

def skip_chunk(file, chunk):
    file.seek(chunk.size_in_bytes, io.SEEK_CUR)

def data_seq(file, int_count_per_unit, string_format, int_count_of_indices, chunk):
    temp_seq = None
    bytes_read = 4
    if(int_count_of_indices > 0):
        temp_seq = []
        if(int_count_per_unit > 1):
            for i in range(int_count_of_indices):
                bytes_to_read = struct.calcsize('<{0}{1}'.format(int_count_per_unit, string_format))
                temp_seq.append(struct.unpack('<{0}{1}'.format(int_count_per_unit, string_format),
                file.read(bytes_to_read)))
                bytes_read += bytes_to_read
        else:
            for i in range(int_count_of_indices):
                bytes_to_read = struct.calcsize('<{0}{1}'.format(int_count_per_unit, string_format))
                temp_seq.append(struct.unpack('<{0}{1}'.format(int_count_per_unit, string_format),
                file.read(bytes_to_read))[0])
                bytes_read += bytes_to_read
    else:
        bytes_to_read = struct.calcsize('<{0}{1}'.format(int_count_per_unit, string_format))
        temp_seq = struct.unpack('<{0}{1}'.format(int_count_per_unit, string_format),
        file.read(bytes_to_read))
        bytes_read += bytes_to_read
    
    if(int_count_of_indices > 0):
        if(bytes_read < chunk.size_in_bytes):
            file.seek(chunk.size_in_bytes-bytes_read, io.SEEK_CUR)
            print('debug:chunksize: ', chunk.size_in_bytes, bytes_read)
            print(chunk.name, hex(file.tell()))

    return temp_seq

def read_weights(file):
    count = u32(file)
    data = []
    for i in range(count*4):
        data.append((u32(file),sf32(file)))
    return data

def update_chunk_dict(chunk, **d):
    chunk.__dict__.update(d)
    #print(d)
        

def read_chunk(file, parent=None):
    chunk = zeroChunk(struct.unpack('<4s', file.read(4))[0].decode('utf-8'),
                    struct.unpack('<I', file.read(4))[0], parent)
    print(chunk)
    if(chunk.name in zero_id_dict.keys()):
        zero_id_dict[chunk.name][0](file, chunk)
    else:
        print('found new chunk: {0}, Offset: {1}\n\n'.format(chunk.name, hex(file.tell())))
        skip_chunk(file, chunk)
    return chunk

def read_subchunks(file, parent):
    bytes_read = 0
    while(bytes_read < parent.size_in_bytes):
        chunk = read_chunk(file, parent)
        parent.addChild(chunk)
        bytes_read += chunk.size_in_bytes+8

def read_indexed_subchunks(file, chunk, count):
    for i in range(count):
        chunk.addChild(read_chunk(file, chunk))

def select_chunk_from_id(id, chunk, rec = 0):
    
    selection = chunk
    #print(selection)
    if(selection.name == id):
        return selection #keep current
    else:
        if(selection.children):
            for child in selection.children:
                selection = select_chunk_from_id(id, child)
                if(selection != None):    
                    if(selection.name == id):
                        break
        else:
            return None
    return selection

def read_animation_cycle_data(file):
    animation_count = u32(file)
    animation_list = []
    for i in range(animation_count):
        anim = zeroAnimationData(
            struct.unpack('<64s', file.read(64))[0].decode('utf-8').rstrip('\x00'),
            sf32(file),
            u32(file),
            u32(file),
            u32(file))
        
        animation_list.append(anim)

    return animation_list

def read_keyframes_per_bone(file, chunk):
    num_of_bones = u32(file)
    bone_keyframe_list = []
    for i in range(num_of_bones):
        keyframe_data = zeroKeyFrameData(
            u32(file), u32(file), u32(file), u32(file), None, None)

        translations = []
        rotations = []
        for j in range(keyframe_data.num_translation_frames):
            translations.append(zeroFrame(u32(file), data_seq(file, 3, 'f', 0, chunk)))
        for j in range(keyframe_data.num_rotation_frames):
            rotations.append(zeroFrame(u32(file), data_seq(file, 4, 'f', 0, chunk)))

        keyframe_data.translationDataFrames = translations
        keyframe_data.rotationDataFrames = rotations

        bone_keyframe_list.append(keyframe_data)

    return bone_keyframe_list

def read_shadow_mesh(file, chunk):
    num_verts = 0
    num_edges = 0

    verts_list = []
    edges_list = []

    num_verts = u32(file)
    for i in range(num_verts):
        verts_list.append(data_seq(file, 3, 'f', 0, chunk))

    num_edges = u32(file)
    for j in range(num_edges):
        edges_list.append(data_seq(file, 4, 'H', 0, chunk))

    chunk.verts = verts_list
    chunk.edges = edges_list

def read_zero_skeleton(file, chunk):
    chunk.bones = []
    for i in range(u32(file)):
        chunk.bones.append(Zero_Bone(u32(file), u32(file), sf32(file), sf32(file), sf32(file)))

def read_zero_blend_factors(file, chunk):
    chunk.values = []
    for i in range(u32(file)):
        chunk.values.append(Zero_Blend(u32(file), sf32(file)))

def read_cloth_collisions(file, chunk):
    chunk.collisions = []
    chunk.bytes_read = 4
    for i in range(u32(file)):
        chunk.collisions.append(
            ZeroClothCollision(zero_string(file, chunk, True),
            zero_string(file, chunk, True), u32(file), sf32(file),
            sf32(file), sf32(file)))
        chunk.bytes_read += 16
    if(chunk.bytes_read < chunk.size_in_bytes):
        skip = chunk.size_in_bytes - chunk.bytes_read
        file.seek(skip, io.SEEK_CUR)

def read_cloth_weights(file, chunk):
    chunk.weights = []
    chunk.bytes_read = 4
    for i in range(u32(file)):
        chunk.weights.append(zero_string(file, chunk, True))
    if(chunk.bytes_read < chunk.size_in_bytes):
        skip = chunk.size_in_bytes - chunk.bytes_read
        file.seek(skip, io.SEEK_CUR)

class zeroChunk:

    def __init__(self, name='', size_in_bytes=0, parent=None):
        self._name = name
        self._size_in_bytes = size_in_bytes
        self._parent = parent
        self.children = None

    def __repr__(self):
        return 'zeroChunk({0}, {1})'.format(self._name, self._size_in_bytes, self._parent)

    def __str__(self):
        return 'Chunk ID: {0} \nTotal Size: {1}\nParent: {2}\n\n{3}\n\n'.format(self._name,
         self._size_in_bytes, self.parent.name if self.parent else None, self.__dict__)

    def update_size_from_children(self):
        size = 0
        if(self.children != None):
            if(self.name == 'MATL'):
                size += 4
            for child in self.children:
                child.update_size_from_children()
                size += child.size_in_bytes+8
            self._size_in_bytes = size
    
    def update_size(self, size):
        self._size_in_bytes = size


    @property
    def name(self):
        return self._name

    @property
    def size_in_bytes(self):
        return self._size_in_bytes

    @property
    def parent(self):
        return self._parent

    def addChild(self, child):
        if(self.children == None):
            self.children = []
        self.children.append(child)

class zeroAnimationData():

    def __init__(self, animation_name, frame_rate, play_style, start_frame, end_frame):
        self._animation_name = animation_name
        self._play_style = play_style
        self._frame_rate = frame_rate
        self._start_frame = start_frame
        self._end_frame = end_frame

    def __repr__(self):
        return 'zeroAnimationData(animation_name={0}, play_style={1}, frame_rate={2}, start_frame={3}, end_frame={4})\n'.format(
            self._animation_name, self._play_style, self._frame_rate, 
            self._start_frame, self._end_frame
        )

        return super().__repr__()

    @property
    def animation_name(self):
        return self._animation_name

    @property
    def play_style(self):
        return self._play_style

    @property
    def frame_rate(self):
        return self._frame_rate

    @property
    def start_frame(self):
        return self._start_frame

    @property
    def end_frame(self):
        return self._end_frame

class zeroKeyFrameData():

    def __init__(self, 
    crc, 
    keyframe_type,
    num_translation_frames,
    num_rotation_frames,
    translationDataFrames,
    rotationDataFrames):

        self._crc = crc
        self._keyframe_type = keyframe_type
        self._num_translation_frames = num_translation_frames
        self._num_rotation_frames = num_rotation_frames
        self.translationDataFrames = translationDataFrames
        self.rotationDataFrames = rotationDataFrames

    def __repr__(self):
        return 'zeroKeyFrameData(crc={0} ,keyframe_type={1}, num_translation_frames={2}, \
         num_rotation_frames={3}, translationDataFrames={4}, rotationDataFrames={5})\n'.format(
            hex(self._crc), self._keyframe_type, self._num_translation_frames,
            self._num_rotation_frames, self.translationDataFrames, self.rotationDataFrames
        )

    @property
    def crc(self):
        return self._crc
    @property
    def keyframe_type(self):
        return self._keyframe_type
    @property
    def num_translation_frames(self):
        return self._num_translation_frames
    @property
    def num_rotation_frames(self):
        return self._num_rotation_frames
     
class zeroFrame():

    def __init__(self, index, data):
        self._index = index
        self._data = data

    def __repr__(self):
        return 'zeroFrame(index={0}, data={1})\n'.format(self._index, self._data)

    @property
    def index(self):
        return self._index
    @property
    def data(self):
        return self._data

class Zero_Bone():

    def __init__(self, crc, bone_type, constrain, length1, length2):
        self._crc = crc
        self._bone_type = bone_type
        self._constrain = constrain
        self._length1 = length1
        self._length2 = length2

    def __repr__(self):
        return 'Zero_Bone(crc={0}, bone_type={1}, constrain={2}, length1={3}, length2={4})\n'.format(
            hex(self._crc), self._bone_type, self.constrain, self._length1, self._length2
            )

    @property
    def crc(self):
        return self._crc
    @property
    def bone_type(self):
        return self._bone_type
    @property
    def constrain(self):
        return self._constrain
    @property
    def length1(self):
        return self._length1
    @property
    def length2(self):
        return self._length2

class Zero_Blend():

    def __init__(self, crc, value):
        self._crc = crc
        self._value = value

    def __repr__(self):
        return 'Zero_Blend(crc={0}, value={1})\n'.format(
            hex(self._crc), self._value
        )

    @property
    def crc(self):
        return self._crc
    @property
    def value(self):
        return self._value

class ZeroClothCollision():

    def __init__(self, ob_name, ob_parent, col_type, x, y, z):
        self.ob_name = ob_name
        self.ob_parent = ob_parent
        self.col_type = col_type
        self.x = x
        self.y = y
        self.z = z


def parse(filepath):
    with open(filepath, 'rb') as zero_file:
        assert zero_file.read(4) == b'HEDR', "Invalid File"
        zero_file.seek(-4, io.SEEK_CUR)
        root = read_chunk(zero_file)
        return root

def print_chunk_recursive(chunk):
    print(chunk)
    if(chunk.children):
        for child in chunk.children:
            print_chunk_recursive(child)


if __name__ == '__main__':
    if(len(sys.argv) == 2):
        root = parse(sys.argv[1])
        print_chunk_recursive(root)

        print('Debug Skeleton Data::::\n\n\n')

        name_list = dict()

        model_data = select_chunk_from_id('MSH2', root)
        for chunk in model_data.children:
            if(chunk.name == 'MODL'):
                name = select_chunk_from_id('NAME', chunk).data
                name_list.update({msh2_crc.crc(name) : name})
                #print(name, msh2_crc.crc(name))

        skel = select_chunk_from_id('SKL2', root)
        if(skel):
            for bone in skel.bones:
                print(name_list[bone.crc], bone.crc, bone.constrain)
