import struct
import bpy

def read_from_buffer(fmt, data, offset):
    size = struct.calcsize(fmt)
    if offset + size > len(data):
        raise ValueError(f"Attempting to read {size} bytes from offset {offset}, which exceeds buffer size {len(data)}")
    return struct.unpack_from(fmt, data, offset), offset + size

def print_and_log(log_file, message):
    print(message)
    log_file.write(message + "\n")

def print_vector3(data, offset, log_file):
    (x, y, z), offset = read_from_buffer('fff', data, offset)
    message = f"vector3: ({x:+6.2f}; {y:+6.2f}; {z:+6.2f})"
    print_and_log(log_file, message)
    return offset

def print_vector4(data, offset, blender, invert, log_file):
    (x, y, z, w), offset = read_from_buffer('ffff', data, offset)
    if blender:
        if invert:
            x, y, z = -x, -y, -z
        message = f"vector4 (blender, invert): ({x:+6.2f}; {y:+6.2f}; {z:+6.2f}; {w:+6.2f})"
    else:
        message = f"vector4: ({x:+6.2f}; {y:+6.2f}; {z:+6.2f}; {w:+6.2f})"
    print_and_log(log_file, message)
    return offset

def print_triangle(data, offset, log_file):
    (a, b, c), offset = read_from_buffer('HHH', data, offset)
    message = f"triangle: (a={a}, b={b}, c={c})"
    print_and_log(log_file, message)
    return offset

def print_node(data, offset, log_file):
    try:
        (parent_id, node_id, link_in_count, space1), offset = read_from_buffer('hhhh', data, offset)
        (name_length,), offset = read_from_buffer('i', data, offset)
        if name_length > 0 and name_length <= len(data) - offset:
            (name,), offset = read_from_buffer(f'{name_length}s', data, offset)
            name = name.decode(errors='replace')
        else:
            name = ''
        message = f"Node: parent_id={parent_id}, node_id={node_id}, link_in_count={link_in_count}, SPACE1={space1}, name={name[:-1]}"
        print_and_log(log_file, message)
        
        # Reading matrix data
        for _ in range(4):
            offset = print_vector4(data, offset, blender=False, invert=False, log_file=log_file)
        
        return offset, link_in_count
    except (ValueError, struct.error) as e:
        print_and_log(log_file, f"Error reading node at offset {offset}: {e}")
        return offset, link_in_count

def check_next_block(data, offset):
    (next_block,), offset = read_from_buffer('i', data, offset)
    return next_block, offset

def print_mesh(data, offset, log_file, link_in_count):
    try:
        # Go 4 bytes back before reading the vertex count
        offset -= 4
        (vertex_count,), offset = read_from_buffer('i', data, offset)
        (triangle_count,), offset = read_from_buffer('i', data, offset)
        (name_length,), offset = read_from_buffer('i', data, offset)
        if name_length > 0 and name_length <= len(data) - offset:
            (name,), offset = read_from_buffer(f'{name_length}s', data, offset)
            name = name.decode(errors='replace')
        else:
            name = ''
        message = f"Mesh: vertex_count={vertex_count}, triangle_count={triangle_count}, name={name[:-1]}"
        print_and_log(log_file, message)
        
        # Read additional properties
        (unknown1,), offset = read_from_buffer('i', data, offset)
        (material_count,), offset = read_from_buffer('i', data, offset)
        (unknown2,), offset = read_from_buffer('i', data, offset)
        message = f"UNKNOWN1={unknown1}, material_count={material_count}, UNKNOWN2={unknown2}"
        print_and_log(log_file, message)
        
        # Initialize a list to store material names
        materials = []

        # Read materials
        for _ in range(material_count):
            (material_length,), offset = read_from_buffer('i', data, offset)
            if material_length > 0 and material_length <= len(data) - offset:
                (material_name,), offset = read_from_buffer(f'{material_length}s', data, offset)
                material_name = material_name.decode(errors='replace')
                materials.append(material_name)
                # Exclude the last character from material_name before printing
                message = f"Material: {material_name[:-1]}"
                print_and_log(log_file, message)
        
        # Reading link matrices
        (link_out_count,), offset = read_from_buffer('i', data, offset)
        print_and_log(log_file, f"Link out count: {link_out_count}")
        for _ in range(link_out_count):
            for _ in range(4):
                offset = print_vector4(data, offset, blender=False, invert=False, log_file=log_file)
        
        # Reading additional mesh properties
        (index_of_type,), offset = read_from_buffer('h', data, offset)
        message = f"Index of Type: {index_of_type}"
        print_and_log(log_file, message)

        if link_out_count == 0:
            for _ in range(2):
                offset = print_vector3(data, offset, log_file)
            # Handle mesh when link_out_count is 0
            (submesh_count,), offset = read_from_buffer('i', data, offset)
            print_and_log(log_file, f"Submesh Count: {submesh_count}")

            # Read submesh data
            submeshes = []
            # Reading submesh data and corresponding indices
            for i in range(submesh_count):
                submesh_data, offset = read_from_buffer('iiiii', data, offset)
                
                # Define the variables for clarity
                material_index = submesh_data[0]
                submesh_triangle_offset = submesh_data[1]
                submesh_triangle_count = submesh_data[2] + submesh_data[1] - 1
                submesh_vertex_offset = submesh_data[3]
                submesh_vertex_count = submesh_data[4] + submesh_data[3]  - 1

                # Determine the material name
                material_name = materials[material_index] if 0 <= material_index < len(materials) else "No Material"
                message = (f"Submesh {i} Data: Material Index: {material_index} ({material_name[:-1]}), "
                           f"From triangle {submesh_triangle_offset} to triangle {submesh_triangle_count}, "
                           f"From vertex {submesh_vertex_offset} to vertex {submesh_vertex_count}")

                print_and_log(log_file, message)


            # Reading count and int16 blocks for each vertex
            (count,), offset = read_from_buffer('i', data, offset)
            print_and_log(log_file, f"Count={count}")

            data_blocks = []
            for _ in range(count):
                int16_block, offset = read_from_buffer('hhhh', data, offset)
                data_blocks.append(int16_block)
                print_and_log(log_file, f"Int16 Block={int16_block}")

            (flag1, flag2), offset = read_from_buffer('ii', data, offset)
            print_and_log(log_file, f"Flag1={flag1}, Flag2={flag2}")

            # Reading vertices
            print_and_log(log_file, "Vertices:")
            for _ in range(vertex_count):
                offset, message = read_vertex_data(data, offset, log_file, data_blocks)
                print_and_log(log_file, message)

            # Reading triangles
            print_and_log(log_file, "Triangles:")
            for _ in range(triangle_count):
                offset = print_triangle(data, offset, log_file)

            if link_in_count != 0:
                (extra_data_index,), offset = read_from_buffer('h', data, offset)
                print_and_log(log_file, f"Extra Data Index: {extra_data_index}")
            
            # Read int16 flag at the end of the triangles block
            (end_flag,), offset = read_from_buffer('h', data, offset)
            message = f"End Flag: {end_flag}"
            print_and_log(log_file, message)

            # Reading the four xyzw vectors

            # Additional handling based on end_flag
            if end_flag > 100:
                for _ in range(4):
                    offset = print_vector4(data, offset, blender=False, invert=False, log_file=log_file)
            elif 4 <= end_flag <= 17:
                offset += 1  # Go forward 1 byte
                (count,), offset = read_from_buffer('h', data, offset)
                offset += 1  # Skip 1 byte
                offset += count + 16  # Skip the specified bytes plus 16
                
                # Read the int16 flag after the skip
                (next_flag,), offset = read_from_buffer('h', data, offset)
                if next_flag > 100:
                    # Handle case for next_flag > 100
                    for _ in range(4):
                        offset = print_vector4(data, offset, blender=False, invert=False, log_file=log_file)

        else:
            (unknown3,), offset = read_from_buffer('h', data, offset)
            (submesh_count,), offset = read_from_buffer('i', data, offset)
            print_and_log(log_file, f"UNKNOWN3={unknown3}, Submesh Count={submesh_count}")
            
            submeshes = []
            # Reading submesh indices
            submesh_indices = []
            for _ in range(submesh_count):
                (submesh_index,), offset = read_from_buffer('i', data, offset)
                submesh_indices.append(submesh_index)
                print_and_log(log_file, f"Submesh Index: {submesh_index}")

            # Reading submesh data and corresponding indices
            for i in range(submesh_count):
                submesh_data, offset = read_from_buffer('iiiii', data, offset)
                
                # Define the variables for clarity
                material_index = submesh_data[0]
                submesh_triangle_offset = submesh_data[1]
                submesh_triangle_count = submesh_data[2] + submesh_data[1] - 1
                submesh_vertex_offset = submesh_data[3]
                submesh_vertex_count = submesh_data[4] + submesh_data[3] - 1

                # Determine the material name
                material_name = materials[material_index] if 0 <= material_index < len(materials) else "No Material"
                message = (f"Submesh {i} Data: Material Index: {material_index} ({material_name[:-1]}), "
                           f"From triangle {submesh_triangle_offset} to triangle {submesh_triangle_count}, "
                           f"From vertex {submesh_vertex_offset} to vertex {submesh_vertex_count}")

                print_and_log(log_file, message)

                # Read indices for the current submesh
                indices = []
                for _ in range(submesh_indices[i]):
                    (index,), offset = read_from_buffer('i', data, offset)
                    indices.append(index)
                print_and_log(log_file, f"Indices: {indices}")
                
            linked_nodes = []
            for _ in range(link_out_count):
                (linked_node,), offset = read_from_buffer('h', data, offset)
                linked_nodes.append(linked_node)
                print_and_log(log_file, f"Linked Node={linked_node}")
                
            for _ in range(2):
                offset = print_vector3(data, offset, log_file)
                
            for i in range(2):
                (block_index,), offset = read_from_buffer('i', data, offset)
                print_and_log(log_file, f"Block Index {i + 1}: {block_index}")
                            
            (sub_triangle_offset, sub_triangle_count, sub_vertex_offset, sub_vertex_count), offset = read_from_buffer('iiii', data, offset)
            print_and_log(log_file, f"Sub Triangle Offset={sub_triangle_offset}, Sub Triangle Count={sub_triangle_count}, Sub Vertex Offset={sub_vertex_offset}, Sub Vertex Count={sub_vertex_count}")
            
            # Reading count and int16 blocks for each vertex
            (count,), offset = read_from_buffer('i', data, offset)
            print_and_log(log_file, f"Count={count}")

            data_blocks = []
            for _ in range(count):
                int16_block, offset = read_from_buffer('hhhh', data, offset)
                data_blocks.append(int16_block)
                print_and_log(log_file, f"Int16 Block={int16_block}")

            (flag1, flag2), offset = read_from_buffer('ii', data, offset)
            print_and_log(log_file, f"Flag1={flag1}, Flag2={flag2}")

            # Reading vertices
            print_and_log(log_file, "Vertices:")
            for _ in range(vertex_count):
                offset, message = read_vertex_data(data, offset, log_file, data_blocks)
                print_and_log(log_file, message)

            # Reading triangles
            print_and_log(log_file, "Triangles:")
            for _ in range(triangle_count):
                offset = print_triangle(data, offset, log_file)

            (extra_data_index,), offset = read_from_buffer('h', data, offset)
            print_and_log(log_file, f"Extra Data Index: {extra_data_index}")

            # Read int16 flag at the end of the complex block
            (end_flag,), offset = read_from_buffer('h', data, offset)
            message = f"End Flag: {end_flag}"
            print_and_log(log_file, message)

            # Additional handling based on end_flag
            if end_flag > 100:
                for _ in range(4):
                    offset = print_vector4(data, offset, blender=False, invert=False, log_file=log_file)
            elif 4 <= end_flag <= 17:
                offset += 1  # Go forward 1 byte
                (count,), offset = read_from_buffer('h', data, offset)
                offset += 1  # Skip 1 byte
                offset += count + 16  # Skip the specified bytes plus 16
                
                # Read the int16 flag after the skip
                (next_flag,), offset = read_from_buffer('h', data, offset)
                if next_flag > 100:
                    # Handle case for next_flag > 100
                    for _ in range(4):
                        offset = print_vector4(data, offset, blender=False, invert=False, log_file=log_file)

        return offset
    except (ValueError, struct.error) as e:
        print_and_log(log_file, f"Error reading mesh at offset {offset}: {e}")
        return offset

# Define the data type and item type enums
dataType = {
    2: 'vector3',
    1: 'vector2',
    8: 'xyzw',
    5: 'unknown'
}

itemType = {
    0x0000: 'position',
    0x0005: 'uv',
    0x0105: 'normal',
    0x0205: 'unknown205',
    0x0305: 'unknown305',
    0x0405: 'weight',
    0x0505: 'link',
    0x0605: 'unknown605'
}

def read_vertex_data(data, offset, log_file, data_blocks):
    try:
        vertex_info = {}
        for block in data_blocks:
            unknown1, offset_value, dtype, itype = block
            dtype_name = dataType.get(dtype, 'unknown')
            itype_name = itemType.get(itype, 'unknown')

            if dtype_name == 'vector3':
                (x, y, z), offset = read_from_buffer('fff', data, offset)
                vertex_info[itype_name] = (x, y, z)
            elif dtype_name == 'vector2':
                (u, v), offset = read_from_buffer('ff', data, offset)
                vertex_info[itype_name] = (u, v)
            elif dtype_name == 'xyzw':  # Read as xyzw vector
                (x, y, z, w), offset = read_from_buffer('BBBB', data, offset)
                vertex_info[itype_name] = (x, y, z, w)
            elif dtype_name == 'unknown':
                if itype_name == 'weight':
                    (weight1,), offset = read_from_buffer('b', data, offset)
                    (weight2,), offset = read_from_buffer('b', data, offset)
                    (weight3,), offset = read_from_buffer('b', data, offset)
                    (weight4,), offset = read_from_buffer('b', data, offset)
                    vertex_info[itype_name] = (weight1, weight2, weight3, weight4)
                elif itype_name == 'normal':
                    (nx,), offset = read_from_buffer('b', data, offset)
                    (ny,), offset = read_from_buffer('b', data, offset)
                    (nz,), offset = read_from_buffer('b', data, offset)
                    (nw,), offset = read_from_buffer('b', data, offset)
                    vertex_info[itype_name] = (nx, ny, nz, nw)
                elif itype_name == 'unknown605':
                    (unknown605,), offset = read_from_buffer('d', data, offset)
                    vertex_info[itype_name] = unknown605
                elif itype_name == 'link':
                     (x, y, z, w), offset = read_from_buffer('BBBB', data, offset)
                     vertex_info[itype_name] = (x, y, z, w)

        message = "vertex: " + ", ".join([f"{key}={value}" for key, value in vertex_info.items()])
        return offset, message
    except (ValueError, struct.error) as e:
        return offset, f"Error reading vertex data at offset {offset}: {e}"

def parse_data(file_path, log_file_path):
    with open(file_path, "rb") as f, open(log_file_path, "w") as log_file:
        data = f.read()

        offset = 0

        try:
            # Parsing XML Length
            (xml_length,), offset = read_from_buffer('i', data, offset)
            if xml_length <= 0 or xml_length >= len(data):
                raise ValueError(f"Invalid XML length: {xml_length}")

            # Parsing XML
            (xml,), offset = read_from_buffer(f'{xml_length - 2}s', data, offset)
            xml = xml.decode(errors='replace')
            print_and_log(log_file, f"XML: {xml}")

            # Parsing SPACE1, SPACE2, SPACE3
            (space1, space2, space3), offset = read_from_buffer('hhh', data, offset)
            print_and_log(log_file, f"SPACE1: {space1}, SPACE2: {space2}, SPACE3={space3}")

            # Parsing Node Count
            (node_count,), offset = read_from_buffer('i', data, offset)
            if node_count < 0 or node_count > 10000:  # Arbitrary large limit to catch errors
                raise ValueError(f"Invalid node count: {node_count}")
            print_and_log(log_file, f"Node Count: {node_count}")

            # Parsing Limits (vector3[2])
            offset = print_vector3(data, offset, log_file=log_file)
            offset = print_vector3(data, offset, log_file=log_file)

            # Parsing Mesh Count
            (mesh_count,), offset = read_from_buffer('i', data, offset)
            if mesh_count < 0 or mesh_count > 10000:  # Arbitrary large limit to catch errors
                raise ValueError(f"Invalid mesh count: {mesh_count}")
            print_and_log(log_file, f"Mesh Count: {mesh_count}")

            # Parsing Nodes and Meshes
            for i in range(node_count):
                print_and_log(log_file, f"Parsing node {i+1}/{node_count} at offset {offset}")
                offset, link_in_count = print_node(data, offset, log_file=log_file)
                
                # Check if the next 4-byte block is non-zero to determine if it is a mesh
                next_block, new_offset = check_next_block(data, offset)
                if next_block != 0:
                    print_and_log(log_file, f"Parsing mesh at offset {new_offset - 4}")
                    offset = print_mesh(data, new_offset, log_file=log_file, link_in_count=link_in_count)
                else:
                    # If the block is zero, skip it to correctly align for the next node
                    offset = new_offset

        except (ValueError, struct.error) as e:
            print_and_log(log_file, f"Error parsing data: {e}")

def normalize_normal(x, y, z):
    return (x / 255.0 * 2 - 1, y / 255.0 * 2 - 1, z / 255.0 * 2 - 1)

def extract_mesh_data(node):
    vertices = []
    faces = []
    uvs = []
    normals = []
    weights = []

    print("Extracting mesh data...")
    for i, vertex_data in enumerate(node['mesh']['vertices']):
        print(f"Processing vertex {i}: {vertex_data}")
        items = vertex_data['items']
        print(f"Items: {items}")
        position = items[0]['vertex']
        vertex = (position['x'], position['y'], position['z'])
        vertices.append(vertex)
        
        if len(items) > 1 and 'uv' in items[1]:
            uv = items[1]['uv']
            uvs.append((uv['u'], 1 - uv['v']))  # Flip UVs on the Y-axis
        else:
            uvs.append((0, 0))  # Default UV if missing
        
        if len(items) > 2 and 'normal' in items[2]:
            normal = items[2]['normal']
            normalized_normal = normalize_normal(normal['x'], normal['y'], normal['z'])
            normals.append(normalized_normal)
        else:
            normals.append((0, 0, 0))  # Default normal if missing
        
        if len(items) > 4 and 'weight' in items[4]:
            weight_data = items[4]['weight']
            link_indices = items[5]['linkIndex'] if len(items) > 5 and 'linkIndex' in items[5] else [0] * len(weight_data)
            weights.append({link_indices[j]: weight_data[j]['value'] / 255.0 for j in range(len(weight_data))})
        else:
            weights.append({})
    
    print("Extracted vertices:", vertices)
    print("Extracted UVs:", uvs)
    print("Extracted normals:", normals)
    print("Extracted weights:", weights)

    for submesh in node['mesh']['submesh']:
        triangle_offset = submesh['triangleOffset']
        triangle_count = submesh['triangleCount']
        vertex_offset = submesh.get('vertexOffset', 0)

        triangles = node['mesh'].get('triangles', [])

        for i in range(triangle_offset, triangle_offset + triangle_count):
            try:
                index0 = triangles[i]['a'] + vertex_offset
                index1 = triangles[i]['b'] + vertex_offset
                index2 = triangles[i]['c'] + vertex_offset

                max_index = len(vertices) - 1
                if index0 > max_index or index1 > max_index or index2 > max_index:
                    print(f"Skipping invalid face with indices: {index0}, {index1}, {index2}")
                    continue

                face = [index0, index1, index2]
                faces.append(face)

            except Exception as e:
                print(f"Error processing face {i}: {e}")
                break

    print("Extracted faces:", faces)
    return vertices, faces, uvs, normals, weights

def extract_bone_data(json_data):
    bones = {}
    bone_list = []

    for node in json_data['nodes']:
        if 'matrix' in node:
            bone = {
                'name': node['name']['name'],
                'parent_id': node['parentId'],
                'matrix': node['matrix']['matrix'],
                'id': node['id']
            }
            bones[node['id']] = bone
            bone_list.append(bone)

    return bone_list, bones

def create_armature(name, bone_list, bones):
    armature_data = bpy.data.armatures.new(name)
    armature_object = bpy.data.objects.new(name, armature_data)

    bpy.context.collection.objects.link(armature_object)
    bpy.context.view_layer.objects.active = armature_object
    bpy.ops.object.mode_set(mode='EDIT')

    for bone_data in bone_list:
        bone = armature_data.edit_bones.new(bone_data['name'])
        matrix = bone_data['matrix']
        bone.head = (matrix['pos']['x'], matrix['pos']['y'], matrix['pos']['z'])
        bone.tail = (matrix['pos']['x'] + 1, matrix['pos']['y'], matrix['pos']['z'])

        if bone_data['parent_id'] >= 0 and bone_data['parent_id'] in bones:
            parent_bone = armature_data.edit_bones[bones[bone_data['parent_id']]['name']]
            bone.parent = parent_bone

    bpy.ops.object.mode_set(mode='OBJECT')
    return armature_object

def create_mesh_in_blender(name, vertices, faces, uvs, normals, armature):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    
    if uvs:
        uv_layer = mesh.uv_layers.new(name='UVMap')
        for face in mesh.polygons:
            for vert_idx, loop_idx in zip(face.vertices, face.loop_indices):
                if vert_idx < len(uvs):
                    uv_layer.data[loop_idx].uv = uvs[vert_idx]
                else:
                    print(f"UV index {vert_idx} out of range")

    if normals:
        loop_normals = []
        for face in mesh.polygons:
            for vert_idx in face.vertices:
                if vert_idx < len(normals):
                    loop_normals.append(normals[vert_idx])
                else:
                    loop_normals.append((0, 0, 0))
                    print(f"Normal index {vert_idx} out of range")
        mesh.normals_split_custom_set(loop_normals)
    
    mesh.update()

    mesh_object = bpy.data.objects.new(name, mesh)
    scene = bpy.context.scene
    scene.collection.objects.link(mesh_object)

    modifier = mesh_object.modifiers.new(name='Armature', type='ARMATURE')
    modifier.object = armature
    mesh_object.parent = armature

    return mesh_object

def set_vertex_weights(mesh_object, armature, weights, bones):
    for bone in armature.data.bones:
        group = mesh_object.vertex_groups.new(name=bone.name)
        for vert_idx, weight_data in enumerate(weights):
            for bone_id, weight in weight_data.items():
                if bone_id in bones and bones[bone_id]['name'] == bone.name:
                    print(f"Assigning weight {weight} to vertex {vert_idx} for bone {bone.name}")
                    group.add([vert_idx], weight, 'ADD')

def main():
    input_file = file_path  # Replace with the path to your JSON file

    json_data = read_json(input_file)

    bone_list, bones = extract_bone_data(json_data)
    armature = create_armature('ImportedArmature', bone_list, bones)

    for node in json_data['nodes']:
        if 'mesh' in node:
            print(f"Processing node: {node['name']['name']}")
            vertices, faces, uvs, normals, weights = extract_mesh_data(node)
            mesh_object = create_mesh_in_blender(node['name']['name'], vertices, faces, uvs, normals, armature)
            set_vertex_weights(mesh_object, armature, weights, bones)

    print(f"Mesh and rig imported successfully")

if __name__ == "__main__":
    # Sample placeholder for writing output to file
    with open(output_path, "w") as log_file:
        log_file.write("Parsed data from model file.")
    parse_data(file_path, log_file_path)
