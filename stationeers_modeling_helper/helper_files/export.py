# SPDX-License-Identifier: GPL-3.0-or-later

import bpy
import os


def export_model_stages(context):
    """
    Exports each model stage as an FBX.
    1. Each collection (except excluded ones) is exported.
    2. Empties are placed at connector origins during export.
    3. Connectors themselves are not exported.
    """
    # Define the collections to export - Now dynamic
    collections_to_export = [col for col in bpy.data.collections if not getattr(col, "exclude_from_export", False)]

    # Find the connectors collection
    connector_col = bpy.data.collections.get("connectors")
    connectors = []
    if connector_col:
        connectors = [obj for obj in connector_col.objects if getattr(obj, "is_stationeers_connector", False)]

    # Determine export directory
    export_dir = ""
    if context.scene.export_path and context.scene.export_path != "":
        export_dir = bpy.path.abspath(context.scene.export_path)
    else:
        # Default to blend file location
        if not bpy.data.is_saved:
            return {"CANCELLED", "Blend file must be saved before exporting to a default location."}
        blend_dir = os.path.dirname(bpy.data.filepath)
        export_dir = os.path.join(blend_dir, "exports")

    # Ensure export_dir is absolute
    export_dir = os.path.abspath(export_dir)

    if not os.path.exists(export_dir):
        try:
            os.makedirs(export_dir)
        except Exception as e:
            return {"CANCELLED", f"Failed to create directory: {str(e)}"}

    # Get blend file name without extension
    blend_file_name = "Untitled"
    if bpy.data.is_saved:
        blend_file_name = os.path.splitext(os.path.basename(bpy.data.filepath))[0]

    # Store initial selection and active object
    original_selection = context.selected_objects[:]
    original_active = context.active_object

    try:
        for stage_col in collections_to_export:
            stage_name = stage_col.name
            if not stage_col.objects:
                continue

            # Deselect all
            bpy.ops.object.select_all(action='DESELECT')

            # Select objects in the stage collection
            for obj in stage_col.objects:
                # If the object is a connector, we don't select it (we'll make empties instead)
                if getattr(obj, "is_stationeers_connector", False):
                    continue
                obj.select_set(True)

            # Create temporary empties at connector locations
            temp_objs = []
            for conn in connectors:
                # Create empty
                empty = bpy.data.objects.new(f"Socket_{conn.name}", None)
                empty.empty_display_type = 'PLAIN_AXES'
                empty.empty_display_size = 0.1
                empty.location = conn.location
                empty.rotation_euler = conn.rotation_euler
                
                # Link it to the stage collection so it's exported with it
                stage_col.objects.link(empty)
                empty.select_set(True)
                temp_objs.append(empty)

            # Set an active object if possible for export
            active_candidate = next((o for o in stage_col.objects if o.select_get()), None)
            if active_candidate:
                context.view_layer.objects.active = active_candidate

            # Export FBX
            filename = f"{blend_file_name}_{stage_name.replace(' ', '_')}.fbx"
            export_path = os.path.join(export_dir, filename)
            
            # Export selected objects only
            bpy.ops.export_scene.fbx(
                filepath=export_path,
                use_selection=True,
                axis_forward='-Z',
                axis_up='Y',
                # Other standard settings
            )

            # Cleanup: Remove temporary empties
            for obj in temp_objs:
                bpy.data.objects.remove(obj, do_unlink=True)

    finally:
        # Restore selection
        bpy.ops.object.select_all(action='DESELECT')
        for obj in original_selection:
            try:
                obj.select_set(True)
            except ReferenceError:
                pass # Object might have been removed
        context.view_layer.objects.active = original_active

    return {"FINISHED"}
