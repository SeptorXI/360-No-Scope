package steven.rangersnipers;

import com.hypixel.hytale.codec.*;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.protocol.*;
import com.hypixel.hytale.server.core.entity.InteractionContext;
import com.hypixel.hytale.server.core.modules.interaction.interaction.CooldownHandler;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.*;
import com.hypixel.hytale.server.core.modules.projectile.ProjectileModule;
import com.hypixel.hytale.server.core.modules.projectile.interaction.ProjectileInteraction;
import com.hypixel.hytale.server.core.modules.projectile.config.ProjectileConfig;
import com.hypixel.hytale.server.core.modules.projectile.component.*;
import com.hypixel.hytale.server.core.modules.projectile.event.ProjectileLaunchEvent;
import com.hypixel.hytale.server.core.util.TargetUtil;
import com.hypixel.hytale.server.core.modules.physics.component.Velocity;
import com.hypixel.hytale.math.vector.Transform;
import com.hypixel.hytale.math.util.HashUtil;
import org.joml.Vector3d;

/** One authoritative shell launch, one ammo payment, several physical pellets. */
public final class ScatterInteraction extends ProjectileInteraction {
    public static final BuilderCodec<ScatterInteraction> CODEC=BuilderCodec.builder(ScatterInteraction.class,
        ScatterInteraction::new,ProjectileInteraction.CODEC)
        .append(new KeyedCodec<>("Pellets",Codec.INTEGER),(o,v)->o.pellets=v,o->o.pellets).add()
        .append(new KeyedCodec<>("SpreadDegrees",Codec.DOUBLE),(o,v)->o.spread=v,o->o.spread).add()
        .append(new KeyedCodec<>("BodyDamage",Codec.DOUBLE),(o,v)->o.body=v,o->o.body).add()
        .append(new KeyedCodec<>("HeadDamage",Codec.DOUBLE),(o,v)->o.head=v,o->o.head).add()
        .append(new KeyedCodec<>("Range",Codec.DOUBLE),(o,v)->o.range=v,o->o.range).add().build();
    private int pellets;private double spread,body,head,range;
    public ScatterInteraction(){}
    // Inherit native Projectile packet, Client wait and simulation. The client
    // supplies its click-time aim and central prediction UUID through that protocol.
    @Override protected void firstRun(InteractionType t,InteractionContext c,CooldownHandler cd){
        var buffer=c.getCommandBuffer();var owner=c.getOwningEntity();
        var profile=ProjectileConfig.getAssetMap().getAsset(config);
        if(buffer==null||owner==null||!owner.isValid()||profile==null||pellets<1||pellets>12||
           !Double.isFinite(spread)||spread<0||spread>20||lifetime<=0||!Double.isFinite(lifetime)){
            c.getState().state=InteractionState.Failed;return;
        }
        var serverLook=TargetUtil.getLook(c.getEntity(),buffer);
        var velocity=buffer.getComponent(c.getEntity(),Velocity.getComponentType());
        double velocitySquared=velocity==null?0:velocity.getClientVelocity().lengthSquared();
        var look=validatedAim(serverLook,c.getClientState(),velocitySquared);
        if(ignorePitch)look.getRotation().setPitch(0);
        if(ignoreYaw)look.getRotation().setYaw(0);
        if(ignoreRoll)look.getRotation().setRoll(0);
        var forward=new Vector3d(look.getDirection()).normalize();
        var side=new Vector3d(forward).cross(Math.abs(forward.y)>.99?new Vector3d(1,0,0):new Vector3d(0,1,0)).normalize();
        var up=new Vector3d(side).cross(forward).normalize();
        var ledger=pellets>1?new ShotgunLedger(pellets,Math.max(body,head)):null;
        var mods=ImpactModifiers.collect(c,owner,buffer);
        var launchContext=new ProjectileLaunchContext(t,true);
        var client=c.getClientState();
        Long seed=c.getChain()!=null&&c.getEntry()!=null?HashUtil.hash((long)c.getChain().getChainId(),(long)c.getEntry().getIndex()):null;
        for(int i=0;i<pellets;i++){
            // Golden-angle disc keeps the complete pattern deterministic and balanced.
            double radius=pellets==1?Math.sqrt(java.util.concurrent.ThreadLocalRandom.current().nextDouble())*Math.tan(Math.toRadians(spread)):
                i==0?0:Math.sqrt((double)i/(pellets-1))*Math.tan(Math.toRadians(spread));
            double angle=pellets==1?java.util.concurrent.ThreadLocalRandom.current().nextDouble()*Math.PI*2:i*2.399963229728653;
            var direction=new Vector3d(forward).fma(radius*Math.cos(angle),side).fma(radius*Math.sin(angle),up).normalize();
            var ref=ProjectileModule.get().spawnProjectile(i==0&&client!=null?client.generatedUUID:null,seed,owner,buffer,profile,new Vector3d(look.getPosition()),direction,(long)((lifetime+(pellets>1?.25:0))*1000));
            var component=ledger==null?null:new ScatterPellet(ledger,i,body,head,range);
            buffer.run(store->{if(ref.isValid()){
                if(component!=null)store.addComponent(ref,RangerSnipersPlugin.scatterType,component);
                if(mods!=null)store.putComponent(ref,ImpactModifiers.getComponentType(),mods);
                store.putComponent(ref,ProjectileLaunchContext.getComponentType(),launchContext);
            }});
            // Class/enchantment launch hooks see one shell, never six ammunition events.
            if(i==0)buffer.invoke(owner,new ProjectileLaunchEvent(ref,t,true));
        }
    }
    /** Mirrors native0.7.6 ProjectileInteraction's validated click-time transform.
     * The displacement bound is1.25*max(clientVelocitySquared,0.5); invalid
     * packets use authoritative server look. Cone/damage remain server-owned.
     */
    public static Transform validatedAim(Transform server,InteractionSyncData client,double velocitySquared){
        if(client==null||client.attackerPos==null||client.attackerRot==null)return new Transform(server);
        var p=client.attackerPos;var r=client.attackerRot;
        if(!Double.isFinite(p.x)||!Double.isFinite(p.y)||!Double.isFinite(p.z)||
           !Float.isFinite(r.pitch)||!Float.isFinite(r.yaw)||!Float.isFinite(r.roll)||!Double.isFinite(velocitySquared))return new Transform(server);
        double distance=server.getPosition().distanceSquared(p.x,p.y,p.z);
        if(distance>1.25*Math.max(velocitySquared,.5))return new Transform(server);
        return new Transform(p.x,p.y,p.z,r.pitch,r.yaw,r.roll);
    }
}
