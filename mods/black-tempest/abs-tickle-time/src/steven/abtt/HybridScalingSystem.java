package steven.abtt;

import com.airijko.endlessleveling.EndlessLeveling;
import com.airijko.endlessleveling.api.PlayerLikeEntities;
import com.airijko.endlessleveling.classes.ClassWeaponResolver;
import com.airijko.endlessleveling.classes.WeaponConfig;
import com.airijko.endlessleveling.combat.AttackPowerResolver;
import com.airijko.endlessleveling.enums.ClassWeaponType;
import com.airijko.endlessleveling.player.PlayerData;
import com.airijko.endlessleveling.util.WorldContextUtil;
import com.hypixel.hytale.component.*;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.meta.MetaKey;
import com.hypixel.hytale.server.core.modules.entity.damage.*;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

/** Selects two native progression factors for this item's direct hits only.
 * Native combat still applies its normal factors, defenses and procs once.
 */
public final class HybridScalingSystem {
    private HybridScalingSystem(){}
    private static final Object TOKEN=new Object();
    private static final MetaKey<Object> ORIGIN=Damage.META_REGISTRY.registerMetaObject();
    private static final MetaKey<Applied> APPLIED=Damage.META_REGISTRY.registerMetaObject();
    private static final ClassWeaponType[] CASTERS={ClassWeaponType.STAFF,ClassWeaponType.WAND,ClassWeaponType.SPELLBOOK};

    public record Snapshot(String nativeCategory,String selectedClassCategory,double nativeClassMultiplier,
        double selectedClassMultiplier,double nativeStatPct,double strengthStatPct,double sorceryStatPct,
        String selectedStat,double normalization){}
    public record Applied(java.util.UUID playerUuid,float amountBefore,float amountAfter,Snapshot snapshot){}

    // Package-private: only the canonical paid channel/storm dispatch marks native Damage objects.
    static void mark(Damage damage){damage.putMetaObject(ORIGIN,TOKEN);}
    public static Applied applied(Damage damage){return damage.getIfPresentMetaObject(APPLIED);}
    /** Runs inside the canonical ability-origin scope, before dispatch, with no global system ordering changes. */
    public static void apply(Damage damage,CommandBuffer<EntityStore> buffer){
        if(damage.getIfPresentMetaObject(ORIGIN)!=TOKEN||applied(damage)!=null||damage.isCancelled()||
           !Float.isFinite(damage.getAmount())||damage.getAmount()<=0||WorldContextUtil.isEndlessDisabled(buffer.getStore())||
           !(damage.getSource() instanceof Damage.EntitySource source))return;
        var ref=source.getRef();
        if(ref==null||!ref.isValid()||!ArmorCastingSystem.eligible(ref,buffer))return;
        var endless=EndlessLeveling.getInstance();
        if(endless==null||endless.getPlayerDataManager()==null)return;
        var player=buffer.getComponent(ref,PlayerRef.getComponentType());
        var uuid=player!=null&&player.isValid()?player.getUuid():PlayerLikeEntities.resolvePlayerLikeUuid(ref,buffer);
        // get is cache-only; a nonplayer NPC cannot create/load a profile by dealing damage.
        PlayerData data=uuid==null?null:endless.getPlayerDataManager().get(uuid);
        if(data==null)return;
        Snapshot snapshot=snapshot(data,damage.getCause());
        if(snapshot==null)return;
        float before=damage.getAmount();
        double normalized=before*snapshot.normalization();
        if(!Double.isFinite(normalized)||normalized<=0||normalized>Float.MAX_VALUE)return;
        float after=(float)normalized;
        damage.setAmount(after);
        damage.putMetaObject(APPLIED,new Applied(uuid,before,after,snapshot));
    }

    /** Uses loaded managers and the actual empty-hand type/family, never a fabricated caster item.
     * The caster alternatives affect class affinity only; staff equipment stats and weapon-only
     * augments are not supplied. Native stat flat bonuses are included in the resolver's percentage.
     */
    public static Snapshot snapshot(PlayerData data,DamageCause cause){
        var endless=EndlessLeveling.getInstance();
        if(data==null||endless==null||endless.getSkillManager()==null||endless.getClassManager()==null)return null;
        var classes=endless.getClassManager();
        var skills=endless.getSkillManager();
        var augments=endless.getAugmentExecutor();
        String category=ClassWeaponResolver.resolveCategoryKey(ItemStack.EMPTY);
        var type=ClassWeaponResolver.resolve(ItemStack.EMPTY);
        String family=ClassWeaponResolver.familyOf(category);
        var route=ClassWeaponResolver.getStatRoute(ItemStack.EMPTY);
        // Native CombatHookProcessor stores the class multiplier as float and skips nonpositive values.
        double originalClass=nativeClassFactor(classes.getWeaponDamageMultiplier(data,category));
        double bestClass=originalClass;
        String selectedClass=category;
        for(var caster:CASTERS){
            double value=nativeClassFactor(classes.getWeaponDamageMultiplier(data,caster.getConfigKey()));
            if(value>bestClass){bestClass=value;selectedClass=caster.getConfigKey();}
        }
        double[] cache={Double.NaN,Double.NaN};
        double actual=AttackPowerResolver.statChannelBonusPct(skills,augments,data,type,family,
            route==WeaponConfig.WeaponStatRoute.HYBRID,route==WeaponConfig.WeaponStatRoute.SORCERY,cause,cache);
        // PHYSICAL is used only as the resolver's strength selector. The Damage cause stays Lightning.
        double strength=AttackPowerResolver.statChannelBonusPct(skills,augments,data,type,family,
            false,false,DamageCause.PHYSICAL,cache);
        double sorcery=AttackPowerResolver.statChannelBonusPct(skills,augments,data,type,family,
            false,true,cause,cache);
        double bestStat=Math.max(strength,sorcery);
        double denominator=1+actual/100;
        double numerator=1+bestStat/100;
        double normalization=(bestClass/originalClass)*(numerator/denominator);
        if(!Double.isFinite(originalClass)||!Double.isFinite(bestClass)||!Double.isFinite(actual)||
           !Double.isFinite(strength)||!Double.isFinite(sorcery)||denominator<=0||numerator<=0||
           !Double.isFinite(normalization)||normalization<=0)return null;
        return new Snapshot(category,selectedClass,originalClass,bestClass,actual,strength,sorcery,
            strength>sorcery?"Strength":"Sorcery",normalization);
    }
    private static double nativeClassFactor(double multiplier){if(!Double.isFinite(multiplier))return Double.NaN;float value=(float)multiplier;return value>0?value:1;}
}
