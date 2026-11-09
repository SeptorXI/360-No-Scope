"""Blender5.1 native-cube ammo renderer. No external assets or approximate icons."""
from pathlib import Path
import json,math
import bpy
from mathutils import Vector,Euler

ROOT=Path(__file__).resolve().parents[1]


def setup():
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
    scene.render.resolution_x=512;scene.render.resolution_y=512;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.render.film_transparent=True
    scene.view_settings.view_transform='Standard';scene.view_settings.look='Medium High Contrast'
    world=bpy.data.worlds.new('Ammo studio');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.6,.68,.78,1);world.node_tree.nodes['Background'].inputs[1].default_value=.6;scene.world=world
    for name,loc,power,size in [('Key',(-35,-45,65),28000,35),('Fill',(50,-10,20),12000,40),('Rim',(10,40,35),21000,30)]:
        light=bpy.data.lights.new(name,'AREA');light.energy=power;light.size=size
        ob=bpy.data.objects.new(name,light);scene.collection.objects.link(ob);ob.location=loc;ob.rotation_euler=(Vector((0,0,3))-ob.location).to_track_quat('-Z','Y').to_euler()
    camera=bpy.data.cameras.new('Ammo inventory camera');cam=bpy.data.objects.new(camera.name,camera);scene.collection.objects.link(cam);scene.camera=cam;camera.type='ORTHO'
    return scene,cam


def material(name,texture,emission=False):
    mat=bpy.data.materials.new(name);mat.use_nodes=True;tree=mat.node_tree
    tex=tree.nodes.new('ShaderNodeTexImage');tex.image=texture;tex.interpolation='Closest'
    if emission:
        shader=tree.nodes.get('Principled BSDF');tree.nodes.remove(shader);shader=tree.nodes.new('ShaderNodeEmission');shader.inputs['Strength'].default_value=1
        tree.links.new(tex.outputs['Color'],shader.inputs['Color']);tree.links.new(shader.outputs[0],tree.nodes['Material Output'].inputs['Surface'])
    else:
        shader=tree.nodes['Principled BSDF'];tree.links.new(tex.outputs['Color'],shader.inputs['Base Color']);shader.inputs['Roughness'].default_value=.72;shader.inputs['Specular IOR Level'].default_value=.18
    return mat


def part(p,mat):
    signs=[(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]
    faces=[('back',(0,1,2,3)),('front',(5,4,7,6)),('left',(4,0,3,7)),('right',(1,5,6,2)),('top',(3,2,6,7)),('bottom',(4,5,1,0))]
    rot=Euler(tuple(math.radians(x) for x in p['rotation']),'XYZ').to_matrix();verts=[]
    for s in signs:
        v=rot@Vector(tuple(s[i]*p['size'][i]/2 for i in range(3)))+Vector(p['center']);verts.append((v.x,v.z,v.y))
    mesh=bpy.data.meshes.new(p['name']);mesh.from_pydata(verts,[],[f[1] for f in faces]);mesh.materials.append(mat);mesh.uv_layers.new(name='Native cube UV')
    for polygon,(face,_) in zip(mesh.polygons,faces):
        u,v,uu,vv=p['uv'][face];uv=[(u/256,1-vv/256),(uu/256,1-vv/256),(uu/256,1-v/256),(u/256,1-v/256)]
        for loop,point in zip(polygon.loop_indices,uv):mesh.uv_layers.active.data[loop].uv=point
    ob=bpy.data.objects.new(p['name'],mesh);bpy.context.collection.objects.link(ob);return ob,verts


def main():
    scene,cam=setup()
    for f in sorted((ROOT/'source').glob('*.scene.json')):
        data=json.loads(f.read_text());t=data['theme'];texture=bpy.data.images.load(data['texture'])
        lit=material('Native lit '+str(t['index']),texture);bright=material('Selected fullbright '+str(t['index']),texture,True)
        objects=[];verts=[]
        for p in data['parts']:
            ob,v=part(p,bright if p['shading_mode']=='fullbright' else lit);objects.append(ob);verts+=v
        lo=Vector(tuple(min(v[a] for v in verts) for a in range(3)));hi=Vector(tuple(max(v[a] for v in verts) for a in range(3)));center=(lo+hi)/2
        cam.location=center+Vector((45,-75,38));cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
        inv=cam.rotation_euler.to_matrix().transposed();view=[inv@(Vector(v)-center) for v in verts]
        width=max(v.x for v in view)-min(v.x for v in view);height=max(v.y for v in view)-min(v.y for v in view);cam.data.ortho_scale=max(width,height)*1.22
        scene.render.filepath=str(ROOT/'previews'/f"Ammo{t['index']:02}.png");bpy.ops.render.render(write_still=True)
        for ob in objects:bpy.data.objects.remove(ob,do_unlink=True)
    print('ORIGINAL_AMMO_RENDERED9')


if __name__=='__main__':main()
