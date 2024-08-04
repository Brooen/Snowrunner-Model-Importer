bl_info = {
    "name": "Snowrunner Model Importer",
    "author": "Brooen",
    "blender": (4, 1, 0),
    "category": "Import-Export",
}

import bpy
import os
from bpy.props import StringProperty, CollectionProperty
from bpy.types import AddonPreferences, Operator
from bpy_extras.io_utils import ImportHelper
from . import model_parser, model_importer, material_importer

class ImporterAddonPreferences(AddonPreferences):
    bl_idname = __name__

    base_path: StringProperty(
        name="Base Textures Path",
        subtype='DIR_PATH',
        description="Base directory for textures",
        default=""
    )

    def draw(self, context):
        layout = self.layout
        layout.label(text="Base Textures Path Should Be Your Editor Folder (Ex: F:\\archives\\snowrunner\\editor\\)")
        layout.prop(self, "base_path")

class ImportModelOperator(Operator, ImportHelper):
    bl_idname = "import_test.model"
    bl_label = "Import Snowrunner Model ([meshes])"
    filename_ext = ""
    filter_glob: StringProperty(
        default="*",
        options={'HIDDEN'},
        maxlen=255,
    )

    files: CollectionProperty(type=bpy.types.PropertyGroup)

    def execute(self, context):
        addon_prefs = context.preferences.addons[__name__].preferences
        base_path = addon_prefs.base_path

        directory = os.path.dirname(self.filepath)
        
        for file in self.files:
            file_path = os.path.join(directory, file.name)
            txt_file_path = os.path.splitext(file_path)[0] + ".txt"

            try:
                # Run the first script to export a txt file
                model_parser.parse_data(file_path, txt_file_path)

                # Run the second script to read the txt file and add model data to the scene
                model_importer.import_model(txt_file_path)

                # Run the third script to add material data
                material_importer.import_materials(txt_file_path, base_path)

            finally:
                # Delete the txt file after importing
                if os.path.exists(txt_file_path):
                    os.remove(txt_file_path)

        return {'FINISHED'}

def menu_func_import(self, context):
    self.layout.operator(ImportModelOperator.bl_idname, text="Import Snowrunner Model ([meshes])")

def register():
    bpy.utils.register_class(ImportModelOperator)
    bpy.utils.register_class(ImporterAddonPreferences)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)

def unregister():
    bpy.utils.unregister_class(ImportModelOperator)
    bpy.utils.unregister_class(ImporterAddonPreferences)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)

if __name__ == "__main__":
    register()
