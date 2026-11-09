"""Blender background renderer for the original art, using the exact source cube data.
Usage: blender --background --factory-startup --python render_art.py
"""
from pathlib import Path
import json
import math
import sys
import bpy
from mathutils import Vector, Quaternion, Euler

ROOT = Path(__file__).resolve().parents[1]


def setup():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 24
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 640
    scene.render.resolution_y = 640
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'Medium High Contrast'
    scene.world.color = (.35, .35, .35)
    world=bpy.data.worlds.new('Soft studio world')
    world.use_nodes=True
    world.node_tree.nodes['Background'].inputs[0].default_value=(.63,.69,.77,1)
    world.node_tree.nodes['Background'].inputs[1].default_value=.7
    scene.world=world
    for name,loc,power,size in [('Key',(-30,-60,100),100000,90),('Fill',(20,80,40),70000,75),('Rim',(-65,30,70),90000,65)]:
        light=bpy.data.lights.new(name,'AREA'); light.energy=power; light.shape='DISK';light.size=size
        ob=bpy.data.objects.new(name,light);scene.collection.objects.link(ob);ob.location=loc
        ob.rotation_euler=(Vector((-8,0,0))-ob.location).to_track_quat('-Z','Y').to_euler()
    camera=bpy.data.cameras.new('Inventory camera');cam=bpy.data.objects.new('Inventory camera',camera)
    scene.collection.objects.link(cam);scene.camera=cam
    cam.location=(40,-150,80); target=Vector((-10,0,-3))
    cam.rotation_mode='QUATERNION'
    cam.rotation_quaternion=(target-cam.location).to_track_quat('-Z','Y') @ Quaternion((0,0,1),math.radians(-23))
    camera.type='ORTHO';camera.ortho_scale=98
    return scene


def mesh_part(p,material):
    # Faces use native blockymodel face semantics; image V starts at top left.
    coords=[(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]
    faces=[('front',(0,1,2,3)),('back',(5,4,7,6)),('left',(4,0,3,7)),('right',(1,5,6,2)),('top',(3,2,6,7)),('bottom',(4,5,1,0))]
    euler=Euler(tuple(math.radians(v) for v in p['rotation']),'XYZ')
    rot=euler.to_matrix(); center=Vector(p['center'])
    verts=[]
    for c in coords:
        v=rot @ Vector(tuple(c[a]*p['size'][a]/2 for a in range(3)))+center
        verts.append((v.x,v.z,v.y))
    mesh=bpy.data.meshes.new(p['name']);mesh.from_pydata(verts,[],[list(f[1]) for f in faces]);mesh.materials.append(material)
    mesh.uv_layers.new(name='Original pixel atlas')
    for polygon,(face,indices) in zip(mesh.polygons,faces):
        u,v,u2,v2=p['uv'][face]
        uv=[(u/512,1-v2/512),(u2/512,1-v2/512),(u2/512,1-v/512),(u/512,1-v/512)]
        for loop,point in zip(polygon.loop_indices,uv):mesh.uv_layers.active.data[loop].uv=point
    ob=bpy.data.objects.new(p['name'],mesh);bpy.context.collection.objects.link(ob)
    return ob


def main():
    scene=setup();out=ROOT/'previews';out.mkdir(exist_ok=True)
    selected=set(sys.argv[sys.argv.index('--')+1:]) if '--' in sys.argv else set()
    for specfile in sorted((ROOT/'source').glob('*.scene.json')):
        data=json.loads(specfile.read_text());ident=data['theme']['id']
        if selected and ident not in selected:continue
        material=bpy.data.materials.new(ident);material.use_nodes=True
        tree=material.node_tree; shader=tree.nodes.get('Principled BSDF')
        tex=tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(data['texture']);tex.interpolation='Closest'
        tree.links.new(tex.outputs['Color'],shader.inputs['Base Color'])
        shader.inputs['Roughness'].default_value=.77
        shader.inputs['Specular IOR Level'].default_value=.18
        emission=bpy.data.materials.new(ident+'_selected_fullbright');emission.use_nodes=True
        et=emission.node_tree;et.nodes.clear()
        emit=et.nodes.new('ShaderNodeEmission');emit.inputs['Strength'].default_value=1.0
        output=et.nodes.new('ShaderNodeOutputMaterial');image=et.nodes.new('ShaderNodeTexImage');image.image=tex.image;image.interpolation='Closest'
        et.links.new(image.outputs['Color'],emit.inputs['Color']);et.links.new(emit.outputs[0],output.inputs['Surface'])
        objects=[mesh_part(p,emission if p.get('shading_mode')=='fullbright' else material) for p in data['parts']]
        legendary=any(p.get('shading_mode')=='fullbright' for p in data['parts'])
        if legendary:
            # Inventory stays clearly lit. The main preview is a labeled dusk
            # study, with glow simulated from the actual selected fullbright cubes.
            scene.render.use_compositing=False
            scene.render.filepath=str(out/(ident+'_Inventory.png'))
            bpy.ops.render.render(write_still=True)
            for ob in scene.objects:
                if ob.type=='LIGHT':ob.data.energy*=.14
            scene.world.node_tree.nodes['Background'].inputs[1].default_value=.11
            core=next(a for a in data['anchors'] if a['name']=='Energy_Core')['position']
            light=bpy.data.lights.new(ident+'_simulated_core_spill','POINT');light.energy=850;light.shadow_soft_size=4
            light.color=(1,.43,.12) if ident=='Tier05' else (.27,.78,1)
            spill=bpy.data.objects.new(light.name,light);scene.collection.objects.link(spill)
            spill.location=(core[0],core[2]-6,core[1]+5)
            ct=bpy.data.node_groups.new(ident+'_simulated_dusk','CompositorNodeTree');scene.compositing_node_group=ct
            ct.interface.new_socket(name='Image',in_out='OUTPUT',socket_type='NodeSocketColor')
            source=ct.nodes.new('CompositorNodeRLayers');glare=ct.nodes.new('CompositorNodeGlare');result=ct.nodes.new('NodeGroupOutput')
            glare.inputs['Type'].default_value='Fog Glow';glare.inputs['Quality'].default_value='High'
            glare.inputs['Threshold'].default_value=.65;glare.inputs['Size'].default_value=.2;glare.inputs['Strength'].default_value=.35
            ct.links.new(source.outputs['Image'],glare.inputs['Image']);ct.links.new(glare.outputs['Image'],result.inputs['Image'])
            scene.render.use_compositing=True
        scene.render.filepath=str(out/(ident+'.png'))
        bpy.ops.render.render(write_still=True)
        if legendary:
            bpy.data.objects.remove(spill,do_unlink=True)
            for ob in scene.objects:
                if ob.type=='LIGHT':ob.data.energy/=.14
            scene.world.node_tree.nodes['Background'].inputs[1].default_value=.7
            scene.render.use_compositing=False
        for ob in objects:bpy.data.objects.remove(ob,do_unlink=True)
    print('ORIGINAL_RANGER_ART_RENDERED')


if __name__=='__main__':main()
