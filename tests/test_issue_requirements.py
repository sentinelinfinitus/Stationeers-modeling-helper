import bpy
import sys

def test_scene_setup():
    print("Testing Scene Setup...")
    # Add a default cube
    bpy.ops.mesh.primitive_cube_add(size=2, location=(0,0,0))
    bpy.data.objects[-1].name = "Cube"
    
    # Run scene setup
    bpy.ops.object.scene_setup()
    
    # Check if Cube is removed
    if "Cube" in bpy.data.objects:
        print("FAILED: Default cube still exists")
        return False
    
    # Check if "scene utils" collection exists
    if "scene utils" not in bpy.data.collections:
        print("FAILED: 'scene utils' collection not created")
        return False
    
    col = bpy.data.collections["scene utils"]
    if col.color_tag != 'COLOR_03':
        print(f"FAILED: Collection color tag is {col.color_tag}, expected COLOR_03")
        return False
        
    print("Scene Setup Test Passed")
    return True

def test_spawn_and_increment():
    print("Testing Spawn and Increment...")
    bpy.ops.object.spawn_bounding_box()
    obj = bpy.context.active_object
    
    if obj.name != "Stationeers_BoundingBox":
        print(f"FAILED: Expected name 'Stationeers_BoundingBox', got '{obj.name}'")
        return False
    
    if obj.users_collection[0].name != "scene utils":
        print(f"FAILED: Object not in 'scene utils' collection, in {obj.users_collection[0].name}")
        return False

    # Test Z increment
    # Initial Z increment is 0, height is 0.5, location.z is 0.25
    if abs(obj.dimensions.z - 0.5) > 0.001 or abs(obj.location.z - 0.25) > 0.001:
        print(f"FAILED: Initial Z dimensions/location wrong: {obj.dimensions.z}, {obj.location.z}")
        return False

    # Increment Z
    bpy.ops.object.increment_bounding_box(axis='Z', direction=1)
    # Z increment 1 -> height 1.0, location.z 0.5
    if abs(obj.dimensions.z - 1.0) > 0.001 or abs(obj.location.z - 0.5) > 0.001:
        print(f"FAILED: Z +1 dimensions/location wrong: {obj.dimensions.z}, {obj.location.z}")
        return False

    # Decrement Z twice (should stop at 0)
    bpy.ops.object.increment_bounding_box(axis='Z', direction=-1)
    bpy.ops.object.increment_bounding_box(axis='Z', direction=-1)
    
    # Z increment should be 0, height 0.5, location.z 0.25
    if obj["increment_z"] < 0:
         print(f"FAILED: increment_z is {obj['increment_z']}, should be >= 0")
         return False
    
    if abs(obj.dimensions.z - 0.5) > 0.001 or abs(obj.location.z - 0.25) > 0.001:
        print(f"FAILED: Z decrement dimensions/location wrong: {obj.dimensions.z}, {obj.location.z}")
        return False

    print("Spawn and Increment Test Passed")
    return True

if __name__ == "__main__":
    # Clear scene
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    
    success = test_scene_setup() and test_spawn_and_increment()
    
    if not success:
        sys.exit(1)
    sys.exit(0)
