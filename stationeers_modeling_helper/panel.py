# SPDX-License-Identifier: GPL-3.0-or-later

import bpy


class VIEW3D_PT_bounding_box_panel(bpy.types.Panel):
    """Creates a Panel in the 3D View Sidebar"""

    bl_label = "Stationeers Modeling Helper"
    bl_idname = "VIEW3D_PT_bounding_box_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Stationeers"

    def draw(self, context: bpy.types.Context):
        layout = self.layout
        obj = context.active_object

        layout.operator("object.scene_setup", text="Scene Setup")
        layout.operator("object.spawn_bounding_box", text="Spawn Bounding Box")

        if obj and getattr(obj, "is_stationeers_bbox", False):
            layout.separator()
            for axis in ["X", "Y", "Z"]:
                prop_name = f"increment_{axis.lower()}"
                count = getattr(obj, prop_name, 0)

                row = layout.row(align=True)
                row.label(text=f"{axis}:")
                
                # Unextend button
                op = row.operator("object.increment_bounding_box", text=f"-{count}")
                op.axis = axis
                op.direction = -1
                
                # Text box to edit incrementation (using the custom property on the object)
                row.prop(obj, prop_name, text="")
                
                # Extend button
                op = row.operator("object.increment_bounding_box", text=f"+{count}")
                op.axis = axis
                op.direction = 1

            layout.separator()
            layout.label(text="Connectors:")
            layout.prop(context.scene, "connector_selector", text="")
            layout.operator("object.spawn_connector", text="Spawn Connector")
        
        if obj and getattr(obj, "is_stationeers_connector", False):
            layout.separator()
            layout.label(text="Connector Controls:")
            
            for axis in ["X", "Y", "Z"]:
                prop_name = f"connector_increment_{axis.lower()}"
                count = getattr(obj, prop_name, 0)

                row = layout.row(align=True)
                row.label(text=f"{axis}:")
                
                op = row.operator("object.increment_connector", text=f"-{abs(count)}")
                op.axis = axis
                op.direction = -1
                
                row.prop(obj, prop_name, text="")
                
                op = row.operator("object.increment_connector", text=f"+{abs(count)}")
                op.axis = axis
                op.direction = 1

            layout.separator()
            layout.label(text="Rotate Connector:")
            row = layout.row(align=True)
            for axis in ["X", "Y", "Z"]:
                op = row.operator("object.rotate_connector", text=axis)
                op.axis = axis


def register():
    bpy.utils.register_class(VIEW3D_PT_bounding_box_panel)


def unregister():
    bpy.utils.unregister_class(VIEW3D_PT_bounding_box_panel)
