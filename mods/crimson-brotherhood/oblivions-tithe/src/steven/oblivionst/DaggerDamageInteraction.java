package steven.oblivionst;

import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.protocol.InteractionType;
import com.hypixel.hytale.server.core.entity.InteractionContext;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.inventory.InventoryComponent;
import com.hypixel.hytale.server.core.meta.MetaKey;
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.modules.interaction.interaction.CooldownHandler;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.Interaction;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.server.DamageEntityInteraction;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import java.util.*;

/** Native hitbox/damage/animation behavior with provenance attached to this attack only. */
public final class DaggerDamageInteraction extends DamageEntityInteraction {
    public static final BuilderCodec<DaggerDamageInteraction> CODEC=BuilderCodec.builder(
        DaggerDamageInteraction.class,DaggerDamageInteraction::new,DamageEntityInteraction.CODEC).build();
    private static final MetaKey<Map<Ref<EntityStore>,Attempt>> ATTEMPTS=Interaction.META_REGISTRY.registerMetaObject();
    private static final ThreadLocal<Attempt> CURRENT=new ThreadLocal<>();
    public static final MetaKey<DirectHit> DIRECT_HIT=Damage.META_REGISTRY.registerMetaObject();
    public record DirectHit(Ref<EntityStore> owner,ItemStack weapon){}
    private static final class Attempt {
        final Ref<EntityStore> owner,target;final ItemStack weapon;final InteractionType type;
        boolean claimed;
        Attempt(Ref<EntityStore> owner,Ref<EntityStore> target,ItemStack weapon,InteractionType type){this.owner=owner;this.target=target;this.weapon=weapon;this.type=type;}
    }
    public DaggerDamageInteraction(){}
    @Override protected void tick0(boolean first,float time,InteractionType type,InteractionContext c,CooldownHandler cd){
        var commands=c.getCommandBuffer();var owner=c.getOwningEntity();var weapon=c.getHeldItem();
        if(commands==null||owner==null||!owner.isValid()||!Objects.equals(owner,c.getEntity())||
            !isWeapon(weapon)||!isWeapon(InventoryComponent.getItemInHand(commands,owner))){super.tick0(first,time,type,c,cd);return;}
        Map<Ref<EntityStore>,Attempt> attempts=c.getInstanceStore().getIfPresentMetaObject(ATTEMPTS);
        if(attempts==null){attempts=new HashMap<>();c.getInstanceStore().putMetaObject(ATTEMPTS,attempts);}
        // Some selectors fork a separate context per victim; others can reuse a
        // damage-node instance store. Both paths permit one direct hit per victim.
        var target=c.getTargetEntity();
        Attempt attempt=attempts.get(target);
        if(attempt==null){attempt=new Attempt(owner,target,weapon,type);attempts.put(target,attempt);}
        Attempt previous=CURRENT.get();CURRENT.set(attempt);
        try{super.tick0(first,time,type,c,cd);}finally{if(previous==null)CURRENT.remove();else CURRENT.set(previous);}
    }
    public static boolean isWeapon(ItemStack stack){return stack!=null&&!stack.isEmpty()&&!stack.isBroken()&&stack.getQuantity()==1&&OblivionsTithePlugin.ITEM_ID.equals(stack.getItemId());}
    /** Only native damage dispatched while our named melee node is running can be marked. */
    static void capture(Damage damage,Ref<EntityStore> target){
        Attempt a=CURRENT.get();
        if(a==null||a.claimed||!Objects.equals(a.target,target)||
            damage.getSource()==null||damage.getSource().getClass()!=Damage.EntitySource.class||
            !Objects.equals(((Damage.EntitySource)damage.getSource()).getRef(),a.owner)||
            damage.getIfPresentMetaObject(Damage.INTERACTION_TYPE)!=a.type)return;
        a.claimed=true;damage.putMetaObject(DIRECT_HIT,new DirectHit(a.owner,a.weapon));
    }
    /** Disposable native fixtures can exercise the same provenance capture as the graph. */
    public static void runNativeHit(Ref<EntityStore> owner,Ref<EntityStore> target,ItemStack weapon,InteractionType type,Runnable nativeDamage){
        if(!isWeapon(weapon))throw new IllegalArgumentException("Fixture requires this dagger");
        Attempt previous=CURRENT.get();CURRENT.set(new Attempt(owner,target,weapon,type));
        try{nativeDamage.run();}finally{if(previous==null)CURRENT.remove();else CURRENT.set(previous);}
    }
    static void clearThreadContext(){CURRENT.remove();}
}
