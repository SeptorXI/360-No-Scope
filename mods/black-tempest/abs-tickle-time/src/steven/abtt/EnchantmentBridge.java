package steven.abtt;

import java.lang.reflect.Field;
import java.util.*;
import org.herolias.plugin.enchantment.*;

/** Version-pinned, additive eligibility adapter. No existing category or config is broadened. */
public final class EnchantmentBridge implements AutoCloseable {
    public static final String CATEGORY_ID = "ABTT_GAUNTLETS";
    public static final Set<String> SUPPORTED = Set.of("sharpness","durability","sturdy","looting","burn","freeze","poison",
        "protection","ranged_protection","environmental_protection","fast_swim");
    private final Field categories;
    private final Map<EnchantmentType,Set<ItemCategory>> original = new LinkedHashMap<>();
    private ItemCategory category;
    public EnchantmentBridge() {
        try {
            categories=EnchantmentType.class.getDeclaredField("applicableCategories");
            if(categories.getType()!=Set.class)throw new IllegalStateException("Unexpected 1.2.1 category field type");
            categories.setAccessible(true);
            var manager=ItemCategoryManager.getInstance();
            if(manager.getCategoryById(CATEGORY_ID)!=null)throw new IllegalStateException("Gauntlet category ID already registered");
            // Only this ID gets the union of verified casting and native glove enchantments.
            category=new ItemCategory(CATEGORY_ID){@Override public boolean isWeapon(){return false;}@Override public boolean isArmor(){return true;}};
            manager.registerCategory(category);
            manager.registerApiItem(ChannelRules.ITEM_ID,category);
            if(category==null||!CATEGORY_ID.equals(category.getId()))throw new IllegalStateException("Cannot register isolated gauntlet category");
            for(var type:EnchantmentType.values()) {
                Set<ItemCategory> before=Set.copyOf(type.getApplicableCategories());
                if(before.contains(category))throw new IllegalStateException("Gauntlet category unexpectedly already registered: "+type.getId());
                if(!SUPPORTED.contains(type.getId()))continue;
                original.put(type,before);
                var after=new HashSet<>(before);after.add(category);
                categories.set(type,Set.copyOf(after));
                if(!type.canApplyTo(category)||!type.getApplicableCategories().containsAll(before)||type.getApplicableCategories().size()!=before.size()+1)
                    throw new IllegalStateException("Eligibility invariant failed for "+type.getId());
            }
            if(original.size()!=SUPPORTED.size())throw new IllegalStateException("Pinned enchantment roster differs");
            for(var type:EnchantmentType.values())if(type.canApplyTo(category)!=SUPPORTED.contains(type.getId()))
                throw new IllegalStateException("Unexpected gauntlet eligibility "+type.getId());
        } catch(ReflectiveOperationException|RuntimeException failure) {
            // Recover already-added memberships before refusing to load.
            for(var entry:original.entrySet())try {
                Field f=EnchantmentType.class.getDeclaredField("applicableCategories");f.setAccessible(true);f.set(entry.getKey(),entry.getValue());
            }catch(ReflectiveOperationException ignored){}
            throw new IllegalStateException("AB's Tickle Time requires the verified SimpleEnchantments 1.2.1 category adapter",failure);
        }
    }
    public ItemCategory category(){return category;}
    public Map<String,Set<String>> originalCategoryIds(){
        Map<String,Set<String>> out=new LinkedHashMap<>();
        for(var e:original.entrySet()){Set<String>s=new TreeSet<>();for(var c:e.getValue())s.add(c.getId());out.put(e.getKey().getId(),Set.copyOf(s));}
        return Collections.unmodifiableMap(out);
    }
    public static EnchantmentManager manager(){
        var p=org.herolias.plugin.SimpleEnchanting.getInstance();
        if(p==null||p.getEnchantmentManager()==null)throw new IllegalStateException("SimpleEnchantments not initialized");
        return p.getEnchantmentManager();
    }
    @Override public void close(){
        for(var e:original.entrySet())try {
            var current=new HashSet<>(e.getKey().getApplicableCategories());current.remove(category);
            categories.set(e.getKey(),Set.copyOf(current));
        }catch(IllegalAccessException failure){throw new IllegalStateException("Cannot remove gauntlet category membership",failure);}
        original.clear();
    }
}
