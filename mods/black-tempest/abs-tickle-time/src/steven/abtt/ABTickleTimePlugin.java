package steven.abtt;

import com.hypixel.hytale.server.core.plugin.*;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.Interaction;
import java.util.logging.Level;

public final class ABTickleTimePlugin extends JavaPlugin {
    private static ABTickleTimePlugin instance;
    private static final java.util.Set<String> REPORTED=java.util.concurrent.ConcurrentHashMap.newKeySet();
    private EnchantmentBridge enchantments;
    private ArmorCastingSystem armorCasting;
    private GauntletGlowSystem gauntletGlow;
    public ABTickleTimePlugin(JavaPluginInit init){super(init);}
    @Override protected void setup(){
        instance=this;
        enchantments=new EnchantmentBridge();
        getCodecRegistry(Interaction.CODEC).register("ABTTChannel",ChannelInteraction.class,ChannelInteraction.CODEC);
        getCodecRegistry(Interaction.CODEC).register("ABTTStorm",StormInteraction.class,StormInteraction.CODEC);
        StormSystem.initialize(getEntityStoreRegistry().registerComponent(StormSystem.State.class,StormSystem.State::new));
        armorCasting=new ArmorCastingSystem();
        getEntityStoreRegistry().registerSystem(armorCasting);
        getEntityStoreRegistry().registerSystem(new ArmorEnchantments());
        getEntityStoreRegistry().registerSystem(new StormSystem());
        gauntletGlow=new GauntletGlowSystem();
        getEntityStoreRegistry().registerSystem(gauntletGlow);
        getLogger().at(Level.INFO).log("AB's Tickle Time registered: Hands armor + empty hands; primary10-blockLightning, Q Storm of Torment; Magic + Unarmed XP; 11 casting/glove enchantments.");
    }
    @Override protected void shutdown(){if(gauntletGlow!=null)gauntletGlow.close();if(armorCasting!=null)armorCasting.close();if(enchantments!=null)enchantments.close();StormSystem.close();ChannelInteraction.clearAudioGate();instance=null;REPORTED.clear();}
    public EnchantmentBridge enchantmentBridge(){return enchantments;}
    public ArmorCastingSystem armorCastingSystem(){return armorCasting;}
    public GauntletGlowSystem gauntletGlowSystem(){return gauntletGlow;}
    static void report(RuntimeException failure){String message="Gauntlet channel rejected: "+failure;if(instance!=null&&REPORTED.add(message))instance.getLogger().at(Level.WARNING).log(message);}
}
