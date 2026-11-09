"""Render actual native rig key poses; run with Blender --background --python.

This is a weapon-mechanism study, not a claimed in-client avatar screenshot.
All geometry, matching cartridge textures and visibility come from runtime assets.
"""
from pathlib import Path
import json,math,sys
import bpy
from mathutils import Vector,Quaternion,Matrix

ART=Path(__file__).resolve().parents[1]
OUT=ART/'previews/reloads'
PHASES=[0,.23,.37,.61,.94]
COORDS=[(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]
FACES=[('front',(0,1,2,3),(0,1)),('back',(5,4,7,6),(0,1)),('left',(4,0,3,7),(2,1)),('right',(1,5,6,2),(2,1)),('top',(3,2,6,7),(0,2)),('bottom',(4,5,1,0),(0,2))]
def v(d):return Vector([d[k] for k in 'xyz'])
def q(d):return Quaternion([d[k] for k in 'wxyz'])
def sample(keys,t,default):
    if not keys:return default
    if t<=keys[0]['time']:return keys[0]['delta']
    for a,b in zip(keys,keys[1:]):
        if t<=b['time']:
            if isinstance(a['delta'],bool):return a['delta'] if t<b['time'] else b['delta']
            f=(t-a['time'])/max(1,b['time']-a['time'])
            if 'w' in a['delta']:
                z=q(a['delta']).slerp(q(b['delta']),f);return dict(zip('wxyz',z))
            return {k:a['delta'][k]*(1-f)+b['delta'][k]*f for k in a['delta']}
    return keys[-1]['delta']
def tr(n,clip,t):
    tracks=clip['nodeAnimations'].get(n['name'],{});p=v(n['position'])+v(sample(tracks.get('position',[]),t,dict(x=0,y=0,z=0)));rot=q(n['orientation'])@q(sample(tracks.get('orientation',[]),t,dict(x=0,y=0,z=0,w=1)))
    return Matrix.Translation(p)@rot.to_matrix().to_4x4()
def geometry(model,clip,t):
    base=model['nodes'][0]['children'][0]['children'][0]
    root=model['nodes'][0];handle=root['children'][0]
    inv=(tr(root,clip,0)@tr(handle,clip,0)@tr(base,clip,0)).inverted();parts=[]
    def walk(n,parent):
        m=parent@tr(n,clip,t);s=n['shape'];tracks=clip['nodeAnimations'].get(n['name'],{});visible=sample(tracks.get('shapeVisible',[]),t,s['visible'])
        if s['type']=='box' and visible:
            size=[s['settings']['size'][k]*s['stretch'][k] for k in 'xyz'];offset=v(s['offset']);vertices=[]
            for corner in COORDS:
                p=inv@m@(offset+Vector([corner[i]*size[i]/2 for i in range(3)]));vertices.append((p.x,p.z,p.y))
            parts.append((n,vertices))
        for child in n.get('children',[]):walk(child,m)
    for n in model['nodes']:walk(n,Matrix.Identity(4))
    return parts
def mat(image,bright):
    m=bpy.data.materials.new('Selected fullbright' if bright else 'Lit pixel atlas');m.use_nodes=True;tree=m.node_tree;tree.nodes.clear();texture=tree.nodes.new('ShaderNodeTexImage');texture.image=image;texture.interpolation='Closest';out=tree.nodes.new('ShaderNodeOutputMaterial')
    if bright:shader=tree.nodes.new('ShaderNodeEmission');shader.inputs['Strength'].default_value=1
    else:shader=tree.nodes.new('ShaderNodeBsdfPrincipled');shader.inputs['Roughness'].default_value=.74;shader.inputs['Specular IOR Level'].default_value=.17
    tree.links.new(texture.outputs['Color'],shader.inputs['Color' if bright else 'Base Color']);tree.links.new(shader.outputs[0],out.inputs['Surface']);return m
def main():
    OUT.mkdir(parents=True,exist_ok=True);bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=10;scene.cycles.use_denoising=True;scene.render.resolution_x=640;scene.render.resolution_y=360;scene.render.resolution_percentage=100;scene.render.film_transparent=False;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='Standard';scene.view_settings.look='Medium High Contrast'
    world=bpy.data.worlds.new('Mechanism studio');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.055,.077,.11,1);world.node_tree.nodes['Background'].inputs[1].default_value=.55;scene.world=world
    for name,loc,power,size in [('Key',(-25,-60,65),80000,70),('Fill',(25,40,45),60000,60)]:
        light=bpy.data.lights.new(name,'AREA');light.energy=power;light.size=size;ob=bpy.data.objects.new(name,light);scene.collection.objects.link(ob);ob.location=loc;ob.rotation_euler=(Vector((0,0,0))-ob.location).to_track_quat('-Z','Y').to_euler()
    camera=bpy.data.cameras.new('Receiver study camera');cam=bpy.data.objects.new('Receiver study camera',camera);scene.collection.objects.link(cam);scene.camera=cam;camera.type='ORTHO';camera.ortho_scale=61;cam.location=(27,-105,57);target=Vector((-3,-3,0));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
    selected=set(sys.argv[sys.argv.index('--')+1:]) if '--' in sys.argv else set()
    catalog=json.loads((ART/'artcatalog.json').read_text());manifest=[]
    for a in catalog['assets']:
        if selected and str(a['tier']) not in selected:continue
        model=json.loads((ART/'Common'/a['model']).read_text());clip=json.loads((ART/'Common'/a['reload']['first_person']).read_text());image=bpy.data.images.load(str(ART/'Common'/a['texture']));materials=[mat(image,False),mat(image,True)]
        for i,phase in enumerate(PHASES):
            objects=[];frame=round(clip['duration']*phase)
            for n,verts in geometry(model,clip,frame):
                mesh=bpy.data.meshes.new(n['name']);mesh.from_pydata(verts,[],[list(face[1]) for face in FACES]);mesh.uv_layers.new(name='Native exact UVs');mesh.materials.append(materials[n['shape']['shadingMode']=='fullbright']);s=n['shape'];size=s['settings']['size']
                for poly,(face,_,axes) in zip(mesh.polygons,FACES):
                    uv=s['textureLayout'][face]['offset'];x,y=uv['x'],uv['y'];w,h=size['xyz'[axes[0]]],size['xyz'[axes[1]]];coords=[(x/512,1-(y+h)/1024),((x+w)/512,1-(y+h)/1024),((x+w)/512,1-y/1024),(x/512,1-y/1024)]
                    for loop,uv in zip(poly.loop_indices,coords):mesh.uv_layers.active.data[loop].uv=uv
                ob=bpy.data.objects.new(n['name'],mesh);scene.collection.objects.link(ob);objects.append(ob)
            output=OUT/f"{a['tier']:02}_{i}_{frame:03}.png";scene.render.filepath=str(output);bpy.ops.render.render(write_still=True)
            manifest.append(dict(index=a['tier'],item_id=a['item_id'],name=a['name'],frame=frame,phase=phase,path=str(output.relative_to(ART)).replace('\\','/'),visible_shapes=len(objects)))
            for ob in objects:bpy.data.objects.remove(ob,do_unlink=True)
        print('RELOAD_KEYPOSES_RENDERED',a['tier'],flush=True)
    (OUT/'keyposes.json').write_text(json.dumps(dict(scope='Offline weapon-rig mechanism keyposes, not in-client player screenshots',keyposes=manifest),indent=2)+'\n')
if __name__=='__main__':main()
