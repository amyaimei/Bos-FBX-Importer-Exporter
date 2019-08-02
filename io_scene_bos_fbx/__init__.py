# author: tori31001 at gmail.com
# website: http://blenderfbx.render.jp/

bl_info = {
    "name": "Bos FBX Import/Export",
    "author": "Kazuma Hatta",
    "version": (0, 8, 8),
    "blender": (2, 7, 7),
    "location": "File > Import/Export > Bos FBX",
    "description": "Import-Export bos, fbx, io: mesh, skeleton",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Import-Export"}
    
if "bpy" in locals():
    import imp
    if "import_bos_fbx" in locals():
        imp.reload(import_bos_fbx)
    if "export_bos_fbx" in locals():
        imp.reload(export_bos_fbx)

import bpy

from bpy.props import (StringProperty,
                       BoolProperty,
                       FloatProperty,
                       EnumProperty,
                       )

from bpy_extras.io_utils import (ImportHelper,
                                 ExportHelper,
                                 path_reference_mode
                                 )

class BosFbxExportOperator(bpy.types.Operator, ExportHelper):
    bl_idname = "export_scene.bos_fbx"
    bl_label = "Bos Fbx Exporter(.bos/.fbx)"
    
    filename_ext = ".bos"
    fliter_glob = bpy.props.StringProperty(default="*.bos;*.fbx")

    filepath = bpy.props.StringProperty(subtype="FILE_PATH")
        
    path_mode = path_reference_mode

    is_text = BoolProperty(\
        name="text",\
        description="export text fbx",\
        default=False,\
        )

    only_selected = BoolProperty(\
        name="only selected",\
        description="export only selected objects",\
        default=False,\
        )

    imported_node_property = BoolProperty(\
        name="export imported node properties",\
        description="export imported node props including local trans/rot/scale and pivot.",\
        default=False,\
        )

    fit_node_length = BoolProperty(\
        name="fit node length",\
        description="Even if export node properties, apply bone length",\
        default=False,\
        )

    fbx_version = EnumProperty(items = \
        [('FBX SDK 2017', 'FBX SDK 2017', 'FBX SDK 2017'), ('FBX SDK 2018', 'FBX SDK 2018', 'FBX SDK 2018')], name = "SDK")

    def execute(self, context):
        import os, sys
        cmd_folder = os.path.dirname(os.path.abspath(__file__))
        if cmd_folder not in sys.path:
            sys.path.insert(0, cmd_folder)
        import export_bos_fbx

        export_bos_fbx.export_bos_fbx(self.filepath, bpy.context, \
                self.is_text,\
                self.only_selected,\
                self.imported_node_property,\
                self.fit_node_length,\
                self.fbx_version)

        return {'FINISHED'}

    def invoke(self, context, event):
        import os
        binary_dir = os.path.dirname(bpy.app.binary_path)
        binary_dir = os.path.join(binary_dir, "umconv")
        #root, ext = os.path.splitext(self.filepath)
        #is_fbx = ("fbx" in ext or "FBX" in ext)
        if os.path.exists(binary_dir):
            self.filename_ext = ".fbx"

        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def draw(self, context):
        layout = self.layout
        row = layout.row(align=True)
        row.prop(self, "fbx_version")
        row = layout.row(align=True)
        row.prop(self, "is_text")
        row = layout.row(align=True)
        row.prop(self, "only_selected")
        row = layout.row(align=True)
        row.prop(self, "imported_node_property")
        row = layout.row(align=True)
        row.prop(self, "fit_node_length")
  
class BosFbxImportOperator(bpy.types.Operator, ImportHelper):
    bl_idname = "import_scene.bos_fbx"
    bl_label = "Bos Fbx Importer(.bos/.fbx)"
    
    filename_ext = ".bos;.fbx"
    fliter_glob = bpy.props.StringProperty(default="*.bos;*.fbx")

    filepath = bpy.props.StringProperty(subtype="FILE_PATH")
        
    path_mode = path_reference_mode

    triangulate = BoolProperty(\
        name="triangulate",\
        description="triangulate or not",\
        default=False,\
        )

    def execute(self, context):
        import os, sys
        cmd_folder = os.path.dirname(os.path.abspath(__file__))
        if cmd_folder not in sys.path:
            sys.path.insert(0, cmd_folder)
        import import_bos_fbx
        import_bos_fbx.import_bos_fbx(self.filepath, bpy.context, self.triangulate)
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

#
# Registration
#
def menu_func_import(self, context):
    self.layout.operator(BosFbxImportOperator.bl_idname, text="Bos FBX (.bos;.fbx)")

def menu_func_export(self, context):
    self.layout.operator(BosFbxExportOperator.bl_idname, text="Bos FBX (.bos;.fbx)")
    
def register():
    bpy.utils.register_module(__name__)
    bpy.types.INFO_MT_file_import.append(menu_func_import)
    bpy.types.INFO_MT_file_export.append(menu_func_export)

def unregister():
    bpy.utils.unregister_module(__name__)
    bpy.types.INFO_MT_file_import.remove(menu_func_import)
    bpy.types.INFO_MT_file_export.remove(menu_func_export)
    
if __name__ == "__main__":
    register()
