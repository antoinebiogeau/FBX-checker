import subprocess
import os
import json

class UniversalFBXAnaliser:
    @staticmethod
    def check_file(filepath, settings, fix_mode=False, blender_path=""):
        if not blender_path or not os.path.exists(blender_path):
            return [{"name": "Erreur", "status": "Fail", "errors": ["Blender.exe introuvable"]}]

        settings_str = json.dumps(settings)
        fix_val = "True" if fix_mode else "False"

        script_content = f"""
import bpy
import json

def run_qa():
    settings = json.loads('{settings_str}')
    fix_active = {fix_val}
    path = r"{filepath}"
    
    scan_p_mode = settings.get('scan_pivot_mode', 'Bottom Center')
    fix_p_mode = settings.get('fix_pivot_mode', 'Bottom Center')
    
    bpy.ops.wm.read_factory_settings(use_empty=True)
    
    try:
        bpy.ops.import_scene.fbx(filepath=path)
        results = []
        all_objs = bpy.data.objects
        props = [o for o in all_objs if o.type == 'MESH' and not o.name.startswith('UCX_')]
        prop_names = [p.name for p in props]
        modified = False

        for obj in props:
            errs = []
            bpy.context.view_layer.objects.active = obj
            
            # boundingbox
            world_verts = [obj.matrix_world @ v.co for v in obj.data.vertices]
            z_min, z_max = min([v.z for v in world_verts]), max([v.z for v in world_verts])
            
            # pivot
            if settings.get('check_pivot'):
                # Cible du SCAN
                scan_target_z = z_min
                if scan_p_mode == "Center": scan_target_z = (z_min + z_max) / 2
                elif scan_p_mode == "Top Center": scan_target_z = z_max

                # On vérifie si le pivot actuel correspond à la cible du SCAN
                if abs(obj.location.z - scan_target_z) > 0.001 or abs(obj.location.x) > 0.001:
                    if fix_active and settings.get('fix_pivot'):
                        # fix
                        bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
                        bpy.ops.object.mode_set(mode='EDIT')
                        bpy.ops.mesh.select_all(action='SELECT')
                        
                        height = z_max - z_min
                        offset_z = 0
                        if fix_p_mode == "Bottom Center": offset_z = height / 2
                        elif fix_p_mode == "Top Center": offset_z = -height / 2
                        
                        bpy.ops.transform.translate(value=(0, 0, offset_z))
                        bpy.ops.object.mode_set(mode='OBJECT')
                        obj.location = (0,0,0)
                        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
                        modified = True
                    else:
                        errs.append(f"Pivot incorrect (attendu: {{scan_p_mode}})")

            # -Ngon patch
            has_ngons = any(len(p.vertices) > 4 for p in obj.data.polygons)
            if settings.get('check_ngon') and has_ngons:
                if fix_active and settings.get('fix_ngon'):
                    bpy.ops.object.mode_set(mode='EDIT')
                    bpy.ops.mesh.select_all(action='SELECT')
                    bpy.ops.mesh.quads_convert_to_tris()
                    bpy.ops.object.mode_set(mode='OBJECT')
                    modified = True
                else:
                    errs.append("NGons détectés")

            # merge double vertices
            if fix_active and settings.get('fix_double'):
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_all(action='SELECT')
                pre_count = len(obj.data.vertices)
                bpy.ops.mesh.remove_doubles()
                bpy.ops.object.mode_set(mode='OBJECT')
                if len(obj.data.vertices) < pre_count:
                    modified = True

            # polycount
            if settings.get('check_poly'):
                if len(obj.data.polygons) > settings.get('poly_limit', 10000):
                    errs.append(f"Polycount: {{len(obj.data.polygons)}}")

            results.append({{"name": obj.name, "status": "Pass" if not errs else "Fail", "errors": errs}})

        # UCX
        if settings.get('check_ucx'):
            for o in [obj for obj in all_objs if obj.name.startswith('UCX_')]:
                if o.name[4:] not in prop_names:
                    results.append({{"name": o.name, "status": "Fail", "errors": ["Collision orpheline"]}})

        if fix_active and modified:
            bpy.ops.export_scene.fbx(filepath=path, bake_space_transform=True, axis_forward='-Z', axis_up='Y')

        print("RESULT_START" + json.dumps(results) + "RESULT_END")
    except Exception as e:
        print("RESULT_START" + json.dumps([{{'name': 'Error', 'status': 'Fail', 'errors': [str(e)]}}]) + "RESULT_END")

run_qa()
"""
        try:
            process = subprocess.Popen(
                [blender_path, "--background", "--factory-startup", "--python-expr", script_content],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8'
            )
            stdout, stderr = process.communicate()
            if "RESULT_START" in stdout:
                return json.loads(stdout.split("RESULT_START")[1].split("RESULT_END")[0])
            return [{"name": "Blender Error", "status": "Fail", "errors": [f"Console: {stderr[:150]}"]}]
        except Exception as e:
            return [{"name": "System Error", "status": "Fail", "errors": [str(e)]}]