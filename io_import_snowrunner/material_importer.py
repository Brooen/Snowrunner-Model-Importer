import bpy
import os
import re
import fnmatch

def append_shader(shader_blend_path, shader_name):
    with bpy.data.libraries.load(shader_blend_path, link=False) as (data_from, data_to):
        if shader_name in data_from.node_groups:
            data_to.node_groups.append(shader_name)

def find_texture(base_path, texture_name):
    for root, dirs, files in os.walk(base_path):
        for file in files:
            if fnmatch.fnmatch(file, '*' + texture_name):
                return os.path.join(root, file)
    return None

def import_materials(material_data_file_path, base_path):
    shader_name = "Snowrunner Shader"
    shader_blend_path = os.path.join(os.path.dirname(__file__), 'shader.blend')

    # Append the shader if it's not already in the file
    if shader_name not in bpy.data.node_groups:
        append_shader(shader_blend_path, shader_name)

    with open(material_data_file_path, 'r') as file:
        data = file.read()

    materials = re.findall(r'<Material(.*?)\/>', data, re.DOTALL)

    for material_data in materials:
        material_props = dict(re.findall(r'(\w+)="([^"]+)"', material_data))
        material_name = material_props.get('Name')
        if not material_name:
            continue

        print(f"Processing material: {material_name}")

        material_node = bpy.data.materials.get(material_name)
        if material_node is None:
            material_node = bpy.data.materials.new(name=material_name)

        material_node.use_nodes = True
        nodes = material_node.node_tree.nodes
        links = material_node.node_tree.links

        for node in nodes:
            nodes.remove(node)

        shader_node = nodes.new(type='ShaderNodeGroup')
        shader_node.node_tree = bpy.data.node_groups.get(shader_name)

        if shader_node.node_tree is None:
            print(f"Error: Shader '{shader_name}' not found")
            continue

        output_node = nodes.new(type='ShaderNodeOutputMaterial')
        links.new(shader_node.outputs['BSDF'], output_node.inputs['Surface'])

        shader_node.location = (0, 0)
        output_node.location = (200, 0)

        for key, value in material_props.items():
            if key.endswith('Map'):
                texture_name = value.replace('/', '_').replace('\\', '_').replace('.tga', '.dds')
                texture_path = find_texture(base_path, texture_name)
                if not texture_path:
                    print(f"Error: File not found for texture name: {texture_name}")
                    continue

                tex_image = nodes.new('ShaderNodeTexImage')
                tex_image.image = bpy.data.images.load(texture_path)
                tex_image.label = key

                if 'NormalMap' in key or 'ShadingMap' in key:
                    tex_image.image.colorspace_settings.name = 'Non-Color'
                else:
                    tex_image.image.alpha_mode = 'CHANNEL_PACKED'

                if key in shader_node.inputs:
                    links.new(tex_image.outputs['Color'], shader_node.inputs[key])
                    print(f"Connected {key} Color output to {shader_name} input")
                    if key == 'AlbedoMap':
                        if 'Blending' in material_props and material_props['Blending'] == 'alpha':
                            links.new(tex_image.outputs['Alpha'], shader_node.inputs['AlbedoMapAlpha'])
                            material_node.blend_method = 'BLEND'
                            print(f"Set blending method to BLEND for {material_name} due to Blending='alpha'")
                        elif 'AlphaKill' in material_props and material_props['AlphaKill'] == 'True':
                            links.new(tex_image.outputs['Alpha'], shader_node.inputs['AlbedoMapAlpha'])
                            material_node.blend_method = 'BLEND'
                            print(f"Set blending method to BLEND for {material_name} due to AlphaKill='True'")

                tex_image.location = (-200, len(nodes) * -200)

        # Ensure material blend method is set if blending or alpha kill is required
        if ('Blending' in material_props and material_props['Blending'] == 'alpha') or \
           ('AlphaKill' in material_props and material_props['AlphaKill'] == 'True'):
            material_node.blend_method = 'BLEND'
            print(f"Ensured blend method is BLEND for {material_name}")

    print("Material data imported successfully")

