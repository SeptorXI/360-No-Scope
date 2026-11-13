package steven.abtt;

import com.hypixel.hytale.component.*;
import com.hypixel.hytale.component.dependency.*;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.server.core.entity.UUIDComponent;
import com.hypixel.hytale.server.core.entity.effect.EffectControllerComponent;
import com.hypixel.hytale.server.core.asset.type.entityeffect.config.EntityEffect;
import com.hypixel.hytale.server.core.inventory.*;
import com.hypixel.hytale.server.core.meta.MetaKey;
import com.hypixel.hytale.server.core.modules.entity.damage.*;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import org.herolias.plugin.enchantment.*;
import java.util.Set;

/** Bridges only this attack's worn-stack enchantments; native armor systems remain authoritative. */
public final class ArmorEnchantments extends DamageEventSystem {
    public static final MetaKey<ItemStack> WORN_STACK=Damage.META_REGISTRY.registerMetaObject();
    @Override public Query<EntityStore> getQuery(){return Query.any();}
    @Override public Set<Dependency<EntityStore>> getDependencies(){return Set.of(
        new SystemGroupDependency<>(Order.AFTER,DamageModule.get().getFilterDamageGroup()),
        new SystemDependency<>(Order.AFTER,DamageCalculatorSystems.SequenceModifier.class),
        new SystemDependency<>(Order.BEFORE,EnchantmentDamageSystem.class));}
    @Override public void handle(int index,ArchetypeChunk<EntityStore> chunk,Store<EntityStore> store,CommandBuffer<EntityStore> buffer,Damage damage){
        var stack=damage.getIfPresentMetaObject(WORN_STACK);
        if(stack==null||damage.isCancelled()||!Float.isFinite(damage.getAmount())||damage.getAmount()<=0||
           !(damage.getSource() instanceof Damage.EntitySource source))return;
        var manager=EnchantmentBridge.manager();
        double multiplier=manager.calculateDamageMultiplier(stack);
        if(!Double.isFinite(multiplier)||multiplier<0)throw new IllegalStateException("Invalid native Sharpness multiplier");
        if(multiplier!=1){
            damage.setAmount((float)(damage.getAmount()*multiplier));
            EnchantmentEventHelper.fireActivated(buffer.getComponent(source.getRef(),PlayerRef.getComponentType()),stack,
                EnchantmentType.SHARPNESS,manager.getEnchantmentLevel(stack,EnchantmentType.SHARPNESS));
        }
    }
    /** Uses native effects and native loot attribution after an accepted hit, with no fake hand item. */
    public static void afterHit(Ref<EntityStore> owner,Ref<EntityStore> target,Damage damage,CommandBuffer<EntityStore> buffer){
        var stack=damage.getIfPresentMetaObject(WORN_STACK);
        if(stack==null||damage.isCancelled()||!Float.isFinite(damage.getAmount())||damage.getAmount()<=0)return;
        var manager=EnchantmentBridge.manager();
        int[] levels=manager.getEnchantmentLevels(stack,EnchantmentType.BURN,EnchantmentType.FREEZE,EnchantmentType.POISON,EnchantmentType.LOOTING);
        // Empty-hand kills fall through resolveDamageEnchantments to this native attribution record.
        // Native burn/smelting and looting corpse systems consume and clear the same record.
        var uuid=buffer.getComponent(target,UUIDComponent.getComponentType());
        if(uuid!=null&&(levels[0]>0||levels[3]>0))manager.updateDoTEnchantments(uuid.getUuid(),levels[0],levels[3]);
        if(buffer.getComponent(target,DeathComponent.getComponentType())!=null)return;
        if(levels[0]>0)effect(owner,target,stack,EnchantmentType.BURN,levels[0],"BurnEnchantment",buffer);
        if(levels[1]>0){
            int protection=0;
            var armor=buffer.getComponent(target,InventoryComponent.Armor.getComponentType());
            if(armor!=null)protection=manager.sumArmorEnchantmentLevels(armor.getInventory(),EnchantmentType.ENVIRONMENTAL_PROTECTION)[0];
            protection=Math.clamp(protection,0,3);
            String id=protection==0?"FreezeEnchantment":"FreezeEnchantment_EnvProt_"+protection;
            if(EntityEffect.getAssetMap().getAsset(id)==null)id="FreezeEnchantment";
            effect(owner,target,stack,EnchantmentType.FREEZE,levels[1],id,buffer);
        }
        if(levels[2]>0)effect(owner,target,stack,EnchantmentType.POISON,levels[2],"PoisonEnchantment",buffer);
    }
    private static void effect(Ref<EntityStore> owner,Ref<EntityStore> target,ItemStack stack,EnchantmentType type,int level,String id,CommandBuffer<EntityStore> buffer){
        var asset=EntityEffect.getAssetMap().getAsset(id);
        if(asset==null)throw new IllegalStateException("Missing native enchantment effect "+id);
        var controller=buffer.ensureAndGetComponent(target,EffectControllerComponent.getComponentType());
        // addEffect evaluates native ApplyConditions, including fire/slow/poison immunities and fluids.
        if(controller!=null&&controller.addEffect(target,asset,buffer,owner))
            EnchantmentEventHelper.fireActivated(buffer.getComponent(owner,PlayerRef.getComponentType()),stack,type,level);
    }
}
