package steven.rangersnipers;

import com.hypixel.hytale.codec.*;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.protocol.*;
import com.hypixel.hytale.server.core.entity.InteractionContext;
import com.hypixel.hytale.server.core.meta.MetaKey;
import com.hypixel.hytale.server.core.modules.interaction.interaction.CooldownHandler;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.*;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.Interaction;
import com.hypixel.hytale.server.core.modules.projectile.component.ImpactModifiers;
import java.util.*;

/** Collect pellet contacts; only the first context reaches one native damage hit. */
public final class ScatterHitInteraction extends SimpleInstantInteraction {
    public static final BuilderCodec<ScatterHitInteraction> CODEC=BuilderCodec.builder(ScatterHitInteraction.class,
        ScatterHitInteraction::new,SimpleInstantInteraction.CODEC)
        .append(new KeyedCodec<>("Operation",Codec.STRING),(o,v)->o.operation=v,o->o.operation).add()
        .append(new KeyedCodec<>("WeaponId",Codec.STRING),(o,v)->o.weaponId=v,o->o.weaponId).add().build();
    private static final MetaKey<ShotgunLedger.Bucket> BUCKET=Interaction.CONTEXT_META_REGISTRY.registerMetaObject();
    private String operation,weaponId;
    public ScatterHitInteraction() {}
    @Override public WaitForDataFrom getWaitForDataFrom(){return WaitForDataFrom.Server;}
    @Override protected void simulateFirstRun(InteractionType type,InteractionContext c,CooldownHandler cd) {}
    @Override protected void firstRun(InteractionType type,InteractionContext c,CooldownHandler cd) {
        try {
            var buffer=c.getCommandBuffer();var entity=c.getEntity();var target=c.getTargetEntity();
            if(buffer==null||entity==null||!entity.isValid()||target==null||!target.isValid()){fail(c);return;}
            var pellet=buffer.getComponent(entity,RangerSnipersPlugin.scatterType);
            var flight=buffer.getComponent(entity,RangerSnipersPlugin.flightType);
            if(pellet==null||flight==null||!flight.profile().weaponId().equals(weaponId)){fail(c);return;}
            if("Record".equals(operation)) {
                var contact=c.getMetaStore().getIfPresentMetaObject(Interaction.HIT_LOCATION);
                if(contact==null){fail(c);return;}
                String detail=c.getMetaStore().getIfPresentMetaObject(Interaction.HIT_DETAIL);
                double distance=flight.distanceForValidatedContact(contact);
                if(!flight.claimImpact()){fail(c);return;}
                if(distance>pellet.maxRange()){fail(c);return;}
                double base="Head".equals(detail)?pellet.head():pellet.body();
                double damage=base*flight.profile().multiplier(distance);
                var recorded=pellet.ledger().record(target,pellet.index(),damage);
                if(!recorded.leader()){fail(c);return;}
                c.getMetaStore().putMetaObject(BUCKET,recorded.bucket());
            } else if("Commit".equals(operation)) {
                var bucket=c.getMetaStore().removeMetaObject(BUCKET);
                double damage=pellet.ledger().close(bucket);
                var original=ImpactModifiers.resolve(c,entity,buffer);
                Map<String,Float> attrs=new HashMap<>();
                if(original!=null&&original.getAttributes()!=null)attrs.putAll(original.getAttributes());
                attrs.put(FalloffInteraction.ATTRIBUTE,(float)damage);
                c.getMetaStore().putMetaObject(ImpactModifiers.CAST_SNAPSHOT,new ImpactModifiers(attrs,
                    original==null?null:original.getOnHitEffectIds(),original==null?null:original.getElementalCauseId()));
            } else fail(c);
        }catch(RuntimeException e){RangerSnipersPlugin.reportFailure(weaponId,e);fail(c);}
    }
    private static void fail(InteractionContext c){c.getState().state=InteractionState.Failed;}
}
