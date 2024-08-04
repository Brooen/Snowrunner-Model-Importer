import bpy
import math
import re
import mathutils

def parse_vector(vector_string):
    return tuple(map(float, vector_string.strip('()').replace(';', '').split()))

def parse_matrix(vector_strings):
    matrix = []
    for vector_string in vector_strings:
        row = list(map(float, re.findall(r'[-+]?\d*\.\d+|\d+', vector_string)))
        matrix.append(row)
    
    rotation_matrix = mathutils.Matrix((
        (matrix[0][0], matrix[0][1], matrix[0][2]),
        (matrix[1][0], matrix[1][1], matrix[1][2]),
        (matrix[2][0], matrix[2][1], matrix[2][2])
    ))
    
    translation = (matrix[3][1], matrix[3][2], matrix[3][3])
    
    full_matrix = rotation_matrix.to_4x4()
    full_matrix.translation = translation
    
    return full_matrix

def parse_vertex(vertex_string):
    try:
        position_match = re.search(r'position=\(([^)]+)\)', vertex_string)
        uv_match = re.search(r'uv=\(([^)]+)\)', vertex_string)
        normal_match = re.search(r'normal=\(([^)]+)\)', vertex_string)
        weight_match = re.search(r'weight=\(([^)]+)\)', vertex_string)
        link_match = re.search(r'link=\(([^)]+)\)', vertex_string)
        
        position = tuple(map(float, position_match.group(1).split(','))) if position_match else None
        uv = tuple(map(float, uv_match.group(1).split(','))) if uv_match else (0.0, 0.0)
        normal_values = tuple(int(n) for n in normal_match.group(1).split(',')) if normal_match else (128, 128, 128, 255)
        weights = tuple(int(n) for n in weight_match.group(1).split(',')) if weight_match else (0, 0, 0, 0)
        links = tuple(int(n) for n in link_match.group(1).split(',')) if link_match else (0, 0, 0, 0)

        x = (normal_values[0] / 255.0) * 2.0 - 1.0
        y = (normal_values[1] / 255.0) * 2.0 - 1.0
        z = (normal_values[2] / 255.0) * 2.0 - 1.0
        length = math.sqrt(x * x + y * y + z * z)
        normal = (x / length, y / length, z / length)

        return position, uv, normal, weights, links
    except Exception as e:
        print(f"Error parsing vertex: {vertex_string} - {e}")
        return None, None, None, None, None

def parse_face(face_string):
    try:
        parts = face_string.split('(')[1].split(')')[0].split(',')
        face = tuple(int(part.split('=')[1]) for part in parts)
        return face
    except Exception as e:
        print(f"Error parsing face: {face_string} - {e}")
        return None

def parse_material(material_string):
    try:
        name = material_string.split(': ')[1].strip()
        return name
    except Exception as e:
        print(f"Error parsing material: {material_string} - {e}")
        return None

def parse_mesh_name(mesh_string):
    try:
        name = mesh_string.split('name=')[1].strip()
        return name
    except Exception as e:
        print(f"Error parsing mesh name: {mesh_string} - {e}")
        return None

def parse_object_name(object_string):
    try:
        name = object_string.split('name=')[1].strip()
        return name
    except Exception as e:
        print(f"Error parsing object name: {object_string} - {e}")
        return None

def parse_bone(bone_string):
    try:
        parent_id = int(re.search(r'parent_id=(-?\d+)', bone_string).group(1))
        node_id = int(re.search(r'node_id=(\d+)', bone_string).group(1))
        name_match = re.search(r'name=([^,]+)', bone_string)
        name = name_match.group(1).strip() if name_match else None
        return parent_id, node_id, name
    except Exception as e:
        print(f"Error parsing bone: {bone_string} - {e}")
        return None, None, None

def parse_submesh(submesh_string):
    try:
        material_index_match = re.search(r'Material Index: (\d+)', submesh_string)
        triangle_range_match = re.search(r'From triangle (\d+) to triangle (\d+)', submesh_string)
        vertex_range_match = re.search(r'From vertex (\d+) to vertex (\d+)', submesh_string)

        if material_index_match and triangle_range_match and vertex_range_match:
            material_index = int(material_index_match.group(1))
            triangle_start = int(triangle_range_match.group(1))
            triangle_end = int(triangle_range_match.group(2))
            vertex_start = int(vertex_range_match.group(1))
            vertex_end = int(vertex_range_match.group(2))
            return material_index, triangle_start, triangle_end, vertex_start, vertex_end
        else:
            raise ValueError("Incomplete submesh data.")
    except Exception as e:
        print(f"Error parsing submesh: {submesh_string} - {e}")
        return None, None, None, None, None

def import_model(txt_file_path):
    with open(txt_file_path, 'r') as file:
        data = file.readlines()

    objects = {}
    current_object = None
    current_mesh = None
    bones = {}
    vertex_groups = {}
    node_id = None
    linked_nodes = []

    for line in data:
        line = line.strip()
        if line.startswith('Node:'):
            parent_id, node_id, bone_name = parse_bone(line)
            if bone_name is not None:
                bones[node_id] = {
                    "parent_id": parent_id,
                    "name": bone_name,
                    "matrix": []
                }
            object_name = parse_object_name(line)
            current_object = {
                "name": object_name,
                "meshes": [],
                "materials": {},
                "submeshes": [],
                "linked_nodes": []
            }
            objects[object_name] = current_object
        elif line.startswith('Mesh:'):
            mesh_name = parse_mesh_name(line)
            current_mesh = {
                "name": mesh_name,
                "vertices": [],
                "uvs": [],
                "normals": [],
                "faces": [],
                "weights": [],
                "links": []
            }
            current_object["meshes"].append(current_mesh)
        elif line.startswith('Material:'):
            material_name = parse_material(line)
            if material_name:
                if current_mesh["name"] not in current_object["materials"]:
                    current_object["materials"][current_mesh["name"]] = []
                current_object["materials"][current_mesh["name"]].append(material_name)
        elif re.search(r'Submesh \d+ Data:', line):
            material_index, triangle_start, triangle_end, vertex_start, vertex_end = parse_submesh(line)
            if material_index is not None:
                current_object["submeshes"].append({
                    "material_index": material_index,
                    "triangle_start": triangle_start,
                    "triangle_end": triangle_end,
                    "vertex_start": vertex_start,
                    "vertex_end": vertex_end
                })
        elif line.startswith('Linked Node='):
            linked_node_id = int(line.split('=')[1])
            current_object["linked_nodes"].append(linked_node_id)
        elif line.startswith('vertex:'):
            position, uv, normal, weights, links = parse_vertex(line)
            if position is not None:
                current_mesh["vertices"].append(position)
                current_mesh["uvs"].append((uv[0], 1 - uv[1]))
                current_mesh["normals"].append(normal)
                current_mesh["weights"].append(weights)
                current_mesh["links"].append(links)
        elif line.startswith('triangle:'):
            face = parse_face(line)
            if face is not None:
                current_mesh["faces"].append(face)
        elif line.startswith('vector4:'):
            if node_id is not None and node_id in bones:
                bones[node_id]["matrix"].append(line)

    armature = bpy.data.armatures.new('Armature')
    armature_obj = bpy.data.objects.new('Armature', armature)
    bpy.context.scene.collection.objects.link(armature_obj)
    bpy.context.view_layer.objects.active = armature_obj
    bpy.ops.object.mode_set(mode='EDIT')

    bone_objs = {}
    for bone_id, bone_data in bones.items():
        bone = armature.edit_bones.new(bone_data["name"])
        if bone_data["parent_id"] in bone_objs:
            bone.parent = bone_objs[bone_data["parent_id"]]

        matrix = parse_matrix(bone_data["matrix"])
        if bone.parent:
            parent_matrix = bone_objs[bone_data["parent_id"]].matrix
            matrix.translation += parent_matrix.translation

        bone.head = (matrix[3][0], matrix[3][1], matrix[3][2])
        bone.tail = (matrix[3][0], matrix[3][1], matrix[3][2] + 0.1)
        bone.matrix = bpy.context.object.matrix_world @ matrix

        bone_objs[bone_id] = bone

    bpy.ops.object.mode_set(mode='OBJECT')

    for obj_name, obj_data in objects.items():
        for mesh_data in obj_data["meshes"]:
            mesh = bpy.data.meshes.new(mesh_data["name"])
            
            valid_faces = []
            for face in mesh_data["faces"]:
                if all(index < len(mesh_data["vertices"]) for index in face):
                    valid_faces.append(face)
                else:
                    print(f"Invalid face indices: {face}")

            mesh.from_pydata(mesh_data["vertices"], [], valid_faces)
            mesh.update()

            obj = bpy.data.objects.new(obj_name, mesh)
            obj.parent = armature_obj

            linked_node_vertex_groups = {}
            for index, linked_node_id in enumerate(obj_data["linked_nodes"]):
                if linked_node_id in bones:
                    vg = obj.vertex_groups.new(name=bones[linked_node_id]["name"])
                    linked_node_vertex_groups[index] = vg

            scene = bpy.context.scene
            scene.collection.objects.link(obj)

            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)

            mesh.uv_layers.new(name='UVMap')
            uv_layer = mesh.uv_layers.active.data
            for poly in mesh.polygons:
                for loop_index in range(poly.loop_start, poly.loop_start + poly.loop_total):
                    loop_vert_index = mesh.loops[loop_index].vertex_index
                    uv_layer[loop_index].uv = mesh_data["uvs"][loop_vert_index]

            mesh.normals_split_custom_set_from_vertices(mesh_data["normals"])

            for i, (weights, links) in enumerate(zip(mesh_data["weights"], mesh_data["links"])):
                for weight, link in zip(weights, links):
                    if weight > 0:
                        if link < len(current_object["linked_nodes"]):
                            node_id = current_object["linked_nodes"][link]
                            if node_id in linked_node_vertex_groups:
                                print(f"Assigning weight {weight / 255.0} to vertex {i} for node {bones[node_id]['name']}")
                                linked_node_vertex_groups[link].add([i], weight / 255.0, 'REPLACE')

            mod = obj.modifiers.new(name='Armature', type='ARMATURE')
            mod.object = armature_obj

            if mesh_data["name"] in obj_data["materials"]:
                for submesh in obj_data["submeshes"]:
                    if mesh_data["name"] in obj_data["materials"]:
                        if submesh["material_index"] <= len(obj_data["materials"][mesh_data["name"]]):
                            mat_name = obj_data["materials"][mesh_data["name"]][submesh["material_index"]]
                            mat = bpy.data.materials.get(mat_name)
                            if not mat:
                                mat = bpy.data.materials.new(name=mat_name)
                            if not obj.data.materials:
                                obj.data.materials.append(mat)
                            else:
                                obj.data.materials.append(mat)

                            for poly in mesh.polygons:
                                if submesh["triangle_start"] <= poly.index <= submesh["triangle_end"]:
                                    poly.material_index = len(obj.data.materials) - 1

    bpy.context.view_layer.update()
    armature_obj.rotation_euler = (math.radians(90), 0, 0)
    armature_obj.scale = (1, 1, -1)
    armature.name = bpy.path.display_name_from_filepath(txt_file_path)
    bpy.context.view_layer.update()

    print("Model imported successfully.")