package steven.oblivionst;

import com.hypixel.hytale.component.*;
import com.hypixel.hytale.component.dependency.*;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.server.core.modules.entity.damage.*;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import java.util.Set;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/** Observe final native rounded damage, after armor, parry, protection and cancellation. */
public final class VenomHitSystem extends DamageEventSystem {
    // Native nested damage commands defer structural component changes. Until
    // that buffer is applied, later hits must reuse this exact queued instance.
    private static final Map<Ref<EntityStore>,VenomState> PENDING=new ConcurrentHashMap<>();
    @Override public Query<EntityStore> getQuery(){return Query.any();}
    @Override public SystemGroup<EntityStore> getGroup(){return DamageModule.get().getInspectDamageGroup();}
    @Override public Set<Dependency<EntityStore>> getDependencies(){return Set.of(new SystemDependency<>(Order.AFTER,DamageSystems.ApplyDamage.class));}
    @Override public void handle(int index,ArchetypeChunk<EntityStore> chunk,Store<EntityStore> store,CommandBuffer<EntityStore> buffer,Damage damage){
        recordAccepted(chunk.getReferenceTo(index),damage,buffer);
    }
    public static boolean recordAccepted(Ref<EntityStore> target,Damage damage,CommandBuffer<EntityStore> buffer){
        var direct=damage.getIfPresentMetaObject(DaggerDamageInteraction.DIRECT_HIT);
        if(direct==null||damage.isCancelled()||!Float.isFinite(damage.getAmount())||damage.getAmount()<=0||
            !VenomTickSystem.alive(target,buffer)||
            direct.owner()==null||!direct.owner().isValid()||direct.owner().getStore()!=target.getStore())return false;
        // Consume provenance once even if another observer repeats the callback.
        damage.removeMetaObject(DaggerDamageInteraction.DIRECT_HIT);
        var state=stateFor(target,buffer);
        if(state==null)state=PENDING.computeIfAbsent(target,ref->{
            var created=new VenomState();buffer.putComponent(ref,OblivionsTithePlugin.venomComponentType(),created);return created;
        });
        state.ledger.hit(direct.owner());return true;
    }
    public static VenomState stateFor(Ref<EntityStore> target,ComponentAccessor<EntityStore> accessor){
        var actual=accessor.getComponent(target,OblivionsTithePlugin.venomComponentType());
        if(actual!=null){PENDING.remove(target,actual);return actual;}
        return PENDING.get(target);
    }
    static void installed(Ref<EntityStore> target,VenomState state){
        PENDING.remove(target,state);PENDING.keySet().removeIf(ref->!ref.isValid());
    }
    static void clearPending(){PENDING.clear();}
}
