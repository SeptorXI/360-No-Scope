package steven.oblivionst;

import com.hypixel.hytale.component.*;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.tick.EntityTickingSystem;
import com.hypixel.hytale.server.core.modules.entity.damage.*;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatMap;
import com.hypixel.hytale.server.core.modules.entitystats.asset.DefaultEntityStatTypes;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.server.combat.DamageCalculator;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.ziggfreed.mmoskilltree.ability.damage.DotDamageSource;
import java.util.*;

/** Native Poison dispatch preserves resistance/immunity and explicit Daggers XP provenance. */
public final class VenomTickSystem extends EntityTickingSystem<EntityStore> {
    public static final DotDamageSource.Origin ORIGIN=new DotDamageSource.Origin("OT_DaedricVenom",List.of("DAGGERS"),false,false);
    /** Native owned-effect sequence metadata keeps SimpleEnchantments from reusing a newly held weapon's attack enchants. */
    private static final class TickCalculator extends DamageCalculator {TickCalculator(){type=Type.ABSOLUTE;sequentialModifierStep=0;sequentialModifierMinimum=1;}}
    @Override public Query<EntityStore> getQuery(){return OblivionsTithePlugin.venomComponentType();}
    @Override public boolean isParallel(int count,int size){return false;}
    @Override public void tick(float dt,int index,ArchetypeChunk<EntityStore> chunk,Store<EntityStore> store,CommandBuffer<EntityStore> buffer){
        var target=chunk.getReferenceTo(index);var state=chunk.getComponent(index,OblivionsTithePlugin.venomComponentType());
        VenomHitSystem.installed(target,state);
        // Keep the small reusable component after expiry: a queued removal can
        // otherwise race another accepted hit in the same world tick.
        if(!state.ledger.active())return;
        advance(target,state,dt,buffer);
        if(!alive(target,buffer))buffer.tryRemoveComponent(target,OblivionsTithePlugin.venomComponentType());
    }
    public static boolean alive(Ref<EntityStore> target,ComponentAccessor<EntityStore> accessor){
        if(target==null||!target.isValid()||accessor==null||accessor.getComponent(target,DeathComponent.getComponentType())!=null)return false;
        var stats=accessor.getComponent(target,EntityStatMap.getComponentType());
        var health=stats==null?null:stats.get(DefaultEntityStatTypes.getHealth());
        return health!=null&&Float.isFinite(health.get())&&health.get()>health.getMin();
    }
    /** Same operation used by the registered world system and disposable native fixtures. */
    public static List<Damage> advance(Ref<EntityStore> target,VenomState state,double dt,CommandBuffer<EntityStore> buffer){
        if(state==null)return List.of();
        if(!alive(target,buffer)){state.ledger.clear();return List.of();}
        state.ledger.removeOwners(owner->owner==null||!owner.isValid()||owner.getStore()!=target.getStore());
        var pulse=state.ledger.advance(dt);var result=new ArrayList<Damage>();
        for(var portion:pulse.entrySet()){
            if(!alive(target,buffer))break;
            result.add(applyPoison(portion.getKey(),target,portion.getValue(),buffer));
        }
        if(!alive(target,buffer))state.ledger.clear();
        return List.copyOf(result);
    }
    public static Damage applyPoison(Ref<EntityStore> owner,Ref<EntityStore> target,int stacks,CommandBuffer<EntityStore> buffer){
        if(stacks<1||stacks>VenomLedger.MAX_STACKS||owner==null||!owner.isValid()||owner.getStore()!=target.getStore())
            throw new IllegalArgumentException("Invalid poison source/portion");
        var cause=DamageCause.getAssetMap().getAsset("Poison");
        if(cause==null)throw new IllegalStateException("Native Poison damage cause missing");
        var damage=new Damage(new DotDamageSource(owner,ORIGIN),cause,(float)(stacks*VenomLedger.DAMAGE_PER_STACK));
        damage.putMetaObject(DamageCalculatorSystems.DAMAGE_SEQUENCE,new DamageCalculatorSystems.DamageSequence(new DamageCalculatorSystems.Sequence(),new TickCalculator()));
        DamageSystems.executeDamage(target,buffer,damage);
        return damage;
    }
}
