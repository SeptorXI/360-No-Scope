package steven.abtt;

import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.protocol.*;
import com.hypixel.hytale.server.core.entity.InteractionContext;
import com.hypixel.hytale.server.core.entity.InteractionManager;
import com.hypixel.hytale.server.core.modules.interaction.interaction.CooldownHandler;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.SimpleInstantInteraction;
import com.hypixel.hytale.server.core.util.TargetUtil;
import org.joml.Vector3d;

/** Q is a server-authoritative tap, never a second channel or a client-supplied target. */
public final class StormInteraction extends SimpleInstantInteraction {
    public static final BuilderCodec<StormInteraction> CODEC=BuilderCodec.builder(StormInteraction.class,StormInteraction::new,SimpleInstantInteraction.CODEC).build();
    @Override public WaitForDataFrom getWaitForDataFrom(){return WaitForDataFrom.Server;}
    @Override protected void simulateFirstRun(InteractionType type,InteractionContext context,CooldownHandler cooldown){}
    @Override protected void firstRun(InteractionType type,InteractionContext context,CooldownHandler cooldown){
        try{
            var buffer=context.getCommandBuffer();var owner=context.getOwningEntity();
            if(type!=ArmorCastingSystem.STORM_INPUT||buffer==null||!ArmorCastingSystem.empty(context.getHeldItem())){
                context.getState().state=InteractionState.Failed;return;
            }
            var look=TargetUtil.getLook(owner,buffer);
            if(!StormSystem.cast(owner,new Vector3d(look.getPosition()),new Vector3d(look.getDirection()),buffer)){
                context.getState().state=InteractionState.Failed;return;
            }
            // The root's SkipCooldownReset means failed targets never acquire the native cooldown.
            cooldown.resetCooldown(StormSystem.COOLDOWN_ID,StormSystem.COOLDOWN,InteractionManager.DEFAULT_CHARGE_TIMES,false);
        }catch(RuntimeException failure){context.getState().state=InteractionState.Failed;ABTickleTimePlugin.report(failure);}
    }
}
