# SPDX-License-Identifier: GPL-3.0-or-later

import os
import bpy


def get_connector_items(self, context):
    """Scan the connectors folder for FBX files."""
    addon_dir = os.path.dirname(__file__)
    connectors_dir = os.path.join(addon_dir, "modding models", "connectors")
    items = []
    if os.path.exists(connectors_dir):
        files = [f for f in os.listdir(connectors_dir) if f.endswith(".fbx")]
        for i, f in enumerate(files):
            items.append((f, f.replace(".fbx", ""), f"Spawn {f}", i))
    
    if not items:
        items.append(("NONE", "None Found", "No connectors available", 0))
    return items


class OBJECT_OT_scene_setup(bpy.types.Operator):
    """Remove default cube and set up scene if no bounding box exists"""

    bl_idname = "object.scene_setup"
    bl_label = "Scene Setup"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context: bpy.types.Context) -> set[str]:
        # Check if bounding box already exists
        bbox_exists = any("increment_x" in obj for obj in bpy.data.objects)

        if not bbox_exists:
            # Remove default cube
            cube = bpy.data.objects.get("Cube")
            if cube:
                bpy.data.objects.remove(cube, do_unlink=True)
                self.report({"INFO"}, "Default cube removed.")
            else:
                self.report({"INFO"}, "No default cube found.")
        else:
            self.report({"INFO"}, "Bounding box exists, scene setup skipped.")

        # Create or find "scene utils" collection
        collection_name = "scene utils"
        if collection_name not in bpy.data.collections:
            new_col = bpy.data.collections.new(collection_name)
            bpy.context.scene.collection.children.link(new_col)
            # Set color tag to yellow (Blender 4.0+ supports 8 colors: 0-NONE to 8-PURPLE)
            # Color tag 3 is Yellow (at least in many versions, check or use closest)
            new_col.color_tag = 'COLOR_03' # COLOR_03 is Yellow

        return {"FINISHED"}


class OBJECT_OT_spawn_bounding_box(bpy.types.Operator):
    """Spawn a 500mm x 500mm x 500mm bounding box"""

    bl_idname = "object.spawn_bounding_box"
    bl_label = "Spawn Bounding Box"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context: bpy.types.Context) -> set[str]:
        # 500mm = 0.5m
        size = 0.5
        bpy.ops.mesh.primitive_cube_add(size=size, location=(0, 0, size / 2))
        obj = context.active_object
        obj.name = "Stationeers_BoundingBox"
        obj.is_stationeers_bbox = True
        obj.display_type = 'BOUNDS'

        # Initialize increment properties (using the defined IntProperties on the Object)
        obj.increment_x = 0
        obj.increment_y = 0
        obj.increment_z = 0

        # Set dimensions properly, 0.5m in each direction
        obj.dimensions = (size, size, size)
        # Apply scale so dimensions are 1:1 with size
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

        # Move to "scene utils" collection
        collection_name = "scene utils"
        if collection_name not in bpy.data.collections:
            new_col = bpy.data.collections.new(collection_name)
            bpy.context.scene.collection.children.link(new_col)
            new_col.color_tag = 'COLOR_03' # Yellow
        
        col = bpy.data.collections[collection_name]
        
        # Unlink from other collections and link to "scene utils"
        for old_col in obj.users_collection:
            old_col.objects.unlink(obj)
        col.objects.link(obj)

        return {"FINISHED"}


class OBJECT_OT_increment_bounding_box(bpy.types.Operator):
    """Increment/Decrement the bounding box size"""

    bl_idname = "object.increment_bounding_box"
    bl_label = "Increment Bounding Box"
    bl_options = {"REGISTER", "UNDO"}

    axis: bpy.props.EnumProperty(
        items=[
            ("X", "X", "X axis"),
            ("Y", "Y", "Y axis"),
            ("Z", "Z", "Z axis"),
        ]
    )
    direction: bpy.props.IntProperty()  # 1 for extend, -1 for unextend

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return (
            context.active_object is not None
            and getattr(context.active_object, "is_stationeers_bbox", False)
        )

    def execute(self, context: bpy.types.Context) -> set[str]:
        obj = context.active_object
        prop_name = f"increment_{self.axis.lower()}"

        current_val = getattr(obj, prop_name, 0)
        new_val = current_val + self.direction

        # For Z axis, enforce new_val >= 0
        if self.axis == "Z" and new_val < 0:
            new_val = 0

        # Update the property - this will trigger the update callback automatically
        setattr(obj, prop_name, new_val)

        return {"FINISHED"}


class OBJECT_OT_spawn_connector(bpy.types.Operator):
    """Spawn a connector on a face of the bounding box"""

    bl_idname = "object.spawn_connector"
    bl_label = "Spawn Connector"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        # Check if any bounding box exists in the scene
        return any(getattr(obj, "is_stationeers_bbox", False) for obj in bpy.data.objects)

    def execute(self, context: bpy.types.Context) -> set[str]:
        scene = context.scene
        selected_file = scene.connector_selector
        if selected_file == "NONE":
            self.report({"ERROR"}, "No connector selected or found.")
            return {"CANCELLED"}

        # Find the bounding box
        bbox = None
        for obj in bpy.data.objects:
            if getattr(obj, "is_stationeers_bbox", False):
                bbox = obj
                break
        
        if not bbox:
            self.report({"ERROR"}, "No bounding box found.")
            return {"CANCELLED"}

        # Store initial bbox state to ensure it doesn't move
        bbox_initial_loc = bbox.location.copy()

        # Path to the FBX
        addon_dir = os.path.dirname(__file__)
        fbx_path = os.path.join(addon_dir, "modding models", "connectors", selected_file)

        if not os.path.exists(fbx_path):
            self.report({"ERROR"}, f"File not found: {fbx_path}")
            return {"CANCELLED"}

        # Import FBX
        # Using context override to ensure it doesn't mess with selection too much
        # or just deselect everything first
        bpy.ops.object.select_all(action='DESELECT')
        
        # Track objects before import to find the new one
        before_import = set(bpy.data.objects.keys())
        
        bpy.ops.import_scene.fbx(filepath=fbx_path)
        
        # Find the new object(s)
        after_import = set(bpy.data.objects.keys())
        new_objs = [bpy.data.objects[name] for name in after_import - before_import]
        
        if not new_objs:
            # If nothing new was added, check if something was imported but with an existing name
            # Or if it's currently selected
            new_objs = context.selected_objects

        if not new_objs:
            self.report({"ERROR"}, "Failed to import connector.")
            return {"CANCELLED"}
            
        new_obj = new_objs[0] # Take the first imported object
        
        # Ensure it's active and selected
        bpy.ops.object.select_all(action='DESELECT')
        new_obj.select_set(True)
        context.view_layer.objects.active = new_obj
        
        new_obj.name = selected_file.replace(".fbx", "")
        new_obj.is_stationeers_connector = True

        # Ensure "connectors" collection
        collection_name = "connectors"
        if collection_name not in bpy.data.collections:
            new_col = bpy.data.collections.new(collection_name)
            scene.collection.children.link(new_col)
        
        col = bpy.data.collections[collection_name]
        
        # Unlink from other collections and link to "connectors"
        for old_col in list(new_obj.users_collection):
            old_col.objects.unlink(new_obj)
        col.objects.link(new_obj)

        # Placement logic
        # Place on the front face (Y min) at Z=0.25m (snapped to 250mm increment)
        # Origin must be on a face. Front face is at -bbox.dimensions.y / 2
        new_obj.location = (0, bbox_initial_loc.y - bbox.dimensions.y / 2, 0.25)
        
        # Store base location for increments
        new_obj.base_location_x = new_obj.location.x
        new_obj.base_location_y = new_obj.location.y
        new_obj.base_location_z = new_obj.location.z

        # Restore bbox location just in case import moved it
        bbox.location = bbox_initial_loc

        # Initialize connector increments
        new_obj.connector_increment_x = 0
        new_obj.connector_increment_y = 0
        new_obj.connector_increment_z = 0
        
        # Deselect all and select the new object
        bpy.ops.object.select_all(action='DESELECT')
        new_obj.select_set(True)
        context.view_layer.objects.active = new_obj
        
        return {"FINISHED"}


class OBJECT_OT_increment_connector(bpy.types.Operator):
    """Move the connector in 250mm increments"""

    bl_idname = "object.increment_connector"
    bl_label = "Increment Connector"
    bl_options = {"REGISTER", "UNDO"}

    axis: bpy.props.EnumProperty(
        items=[
            ("X", "X", "X axis"),
            ("Y", "Y", "Y axis"),
            ("Z", "Z", "Z axis"),
        ]
    )
    direction: bpy.props.IntProperty()  # 1 for forward, -1 for backward

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return (
            context.active_object is not None
            and getattr(context.active_object, "is_stationeers_connector", False)
        )

    def execute(self, context: bpy.types.Context) -> set[str]:
        obj = context.active_object
        prop_name = f"connector_increment_{self.axis.lower()}"

        current_val = getattr(obj, prop_name, 0)
        new_val = current_val + self.direction

        # Update the property - this will trigger the update callback automatically
        setattr(obj, prop_name, new_val)

        return {"FINISHED"}


class OBJECT_OT_rotate_connector(bpy.types.Operator):
    """Rotate the selected connector"""

    bl_idname = "object.rotate_connector"
    bl_label = "Rotate Connector"
    bl_options = {"REGISTER", "UNDO"}

    axis: bpy.props.EnumProperty(
        items=[
            ("X", "X", "X axis"),
            ("Y", "Y", "Y axis"),
            ("Z", "Z", "Z axis"),
        ]
    )

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return (
            context.active_object is not None
            and getattr(context.active_object, "is_stationeers_connector", False)
        )

    def execute(self, context: bpy.types.Context) -> set[str]:
        import math
        obj = context.active_object
        # Rotate 90 degrees around selected axis (local)
        if self.axis == "X":
            obj.rotation_euler.x += math.radians(90)
        elif self.axis == "Y":
            obj.rotation_euler.y += math.radians(90)
        elif self.axis == "Z":
            obj.rotation_euler.z += math.radians(90)
        return {"FINISHED"}


classes = [
    OBJECT_OT_scene_setup,
    OBJECT_OT_spawn_bounding_box,
    OBJECT_OT_increment_bounding_box,
    OBJECT_OT_spawn_connector,
    OBJECT_OT_increment_connector,
    OBJECT_OT_rotate_connector,
]


def update_connector_location_callback(self, context):
    """Callback for connector increment properties to update location."""
    if not getattr(self, "is_stationeers_connector", False):
        return

    # Base location is where it was spawned. 
    # But wait, we don't store the base location. 
    # Let's assume we use the current position and just add the increment? No, that's not stable.
    # The requirement says "moved in 250mm increments".
    # We should probably store a 'base_location' or just use the increments as absolute values from 0 for now, 
    # but the user said "similar setup to bbox".
    # For bbox, increments are absolute additions to 0.5m.
    
    # Let's add base_location_x/y/z hidden properties to store spawn point?
    # Or just use the increments as offsets from where it is? No.
    
    # If we look at the requirements: "origin can only be placed along 250mm increments of the bounding box"
    # This suggests it should snap to a grid.
    
    self.location.x = self.base_location_x + (self.connector_increment_x * 0.25)
    self.location.y = self.base_location_y + (self.connector_increment_y * 0.25)
    self.location.z = self.base_location_z + (self.connector_increment_z * 0.25)


def update_dimensions_callback(self, context):
    """Callback for increment properties to update object size and keep it on floor."""
    if not getattr(self, "is_stationeers_bbox", False):
        return

    # Ensure Z >= 0 (though UI should handle this, let's be safe)
    if self.increment_z < 0:
        self.increment_z = 0

    # Initial size is 0.5m. Each increment adds 0.5m.
    size_x = 0.5 + (self.increment_x * 0.5)
    size_y = 0.5 + (self.increment_y * 0.5)
    size_z = 0.5 + (self.increment_z * 0.5)

    # Set dimensions directly
    self.dimensions = (max(0.01, float(size_x)), max(0.01, float(size_y)), max(0.01, float(size_z)))

    # To keep bottom at 0, location.z must be half of the height.
    # Using size_z directly is more reliable than self.dimensions.z immediately after setting it.
    self.location.z = size_z / 2


def register():
    # Register properties on Object type
    bpy.types.Object.is_stationeers_bbox = bpy.props.BoolProperty(
        name="Is Stationeers Bounding Box",
        default=False
    )
    bpy.types.Object.is_stationeers_connector = bpy.props.BoolProperty(
        name="Is Stationeers Connector",
        default=False
    )
    bpy.types.Scene.connector_selector = bpy.props.EnumProperty(
        name="Connector",
        description="Select a connector mesh to spawn",
        items=get_connector_items
    )
    bpy.types.Object.increment_x = bpy.props.IntProperty(
        name="Increment X",
        default=0,
        min=0,
        update=update_dimensions_callback
    )
    bpy.types.Object.increment_y = bpy.props.IntProperty(
        name="Increment Y",
        default=0,
        min=0,
        update=update_dimensions_callback
    )
    bpy.types.Object.increment_z = bpy.props.IntProperty(
        name="Increment Z",
        default=0,
        min=0,
        update=update_dimensions_callback
    )
    
    # Connector properties
    bpy.types.Object.connector_increment_x = bpy.props.IntProperty(
        name="Connector Increment X",
        default=0,
        update=update_connector_location_callback
    )
    bpy.types.Object.connector_increment_y = bpy.props.IntProperty(
        name="Connector Increment Y",
        default=0,
        update=update_connector_location_callback
    )
    bpy.types.Object.connector_increment_z = bpy.props.IntProperty(
        name="Connector Increment Z",
        default=0,
        update=update_connector_location_callback
    )
    bpy.types.Object.base_location_x = bpy.props.FloatProperty(name="Base Location X", default=0.0)
    bpy.types.Object.base_location_y = bpy.props.FloatProperty(name="Base Location Y", default=0.0)
    bpy.types.Object.base_location_z = bpy.props.FloatProperty(name="Base Location Z", default=0.0)

    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    # Remove properties from Object type
    del bpy.types.Object.is_stationeers_bbox
    del bpy.types.Object.is_stationeers_connector
    del bpy.types.Scene.connector_selector
    del bpy.types.Object.increment_x
    del bpy.types.Object.increment_y
    del bpy.types.Object.increment_z
    
    del bpy.types.Object.connector_increment_x
    del bpy.types.Object.connector_increment_y
    del bpy.types.Object.connector_increment_z
    del bpy.types.Object.base_location_x
    del bpy.types.Object.base_location_y
    del bpy.types.Object.base_location_z
