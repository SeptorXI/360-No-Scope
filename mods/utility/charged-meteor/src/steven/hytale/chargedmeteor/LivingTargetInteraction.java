package steven.hytale.chargedmeteor;

import com.alechilles.alecstamework.npc.components.TameworkOwnerComponent;
import com.alechilles.alecstamework.npc.components.TameworkTamedComponent;
import com.hypixel.hytale.builtin.companionblockspawner.CompanionBlockSpawnerPlugin;
import com.hypixel.hytale.builtin.companionblockspawner.CompanionSpawnerMarkerReference;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.protocol.InteractionState;
import com.hypixel.hytale.protocol.InteractionType;
import com.hypixel.hytale.protocol.WaitForDataFrom;
import com.hypixel.hytale.server.core.asset.type.attitude.Attitude;
import com.hypixel.hytale.server.core.entity.InteractionContext;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.modules.entity.component.Invulnerable;
import com.hypixel.hytale.server.core.modules.entity.damage.DeathComponent;
import com.hypixel.hytale.server.core.modules.interaction.interaction.CooldownHandler;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.SimpleInstantInteraction;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import com.hypixel.hytale.server.npc.role.support.WorldSupport;
import endgame.plugin.api.PetAPI;
import endgame.plugin.components.RuneSummonComponent;

public final class LivingTargetInteraction extends SimpleInstantInteraction {
    public static final BuilderCodec<LivingTargetInteraction> CODEC = BuilderCodec.builder(
            LivingTargetInteraction.class, LivingTargetInteraction::new, SimpleInstantInteraction.CODEC)
            .build();

    @Override
    public WaitForDataFrom getWaitForDataFrom() {
        return WaitForDataFrom.Server;
    }

    @Override
    protected void simulateFirstRun(InteractionType type, InteractionContext context, CooldownHandler cooldown) {
        // The interaction result comes from the server's target and ownership checks.
    }

    @Override
    protected void firstRun(InteractionType type, InteractionContext context, CooldownHandler cooldown) {
        if (!canHitCreature(context.getTargetEntity(), context.getCommandBuffer())) {
            context.getState().state = InteractionState.Failed;
        }
    }

    static boolean canHitCreature(Ref<EntityStore> target, CommandBuffer<EntityStore> buffer) {
        if (buffer == null || target == null || !target.isValid()) {
            return false;
        }

        NPCEntity npc = buffer.getComponent(target, NPCEntity.getComponentType());
        if (npc == null || npc.isDespawning()
                || buffer.getComponent(target, Player.getComponentType()) != null
                || buffer.getComponent(target, DeathComponent.getComponentType()) != null
                || buffer.getComponent(target, Invulnerable.getComponentType()) != null) {
            return false;
        }

        var support = buffer.getComponent(target, WorldSupport.getComponentType());
        var attitude = support == null ? null : support.getDefaultPlayerAttitude();
        if (attitude == Attitude.FRIENDLY || attitude == Attitude.REVERED) {
            return false;
        }

        String role = npc.getRoleName();
        // Rekindle Embers spawns these vanilla allies without an ownership component.
        return !"Risen_Knight".equals(role) && !"Risen_Gunner".equals(role) && !isCompanion(target, buffer);
    }

    private static boolean isCompanion(Ref<EntityStore> target, CommandBuffer<EntityStore> buffer) {
        var summonType = RuneSummonComponent.getComponentType();
        if (PetAPI.getPetOwner(target) != null
                || (summonType != null && buffer.getComponent(target, summonType) != null)) {
            return true;
        }

        var companionType = CompanionBlockSpawnerPlugin.get() == null
                ? null : CompanionSpawnerMarkerReference.getComponentType();
        if (companionType != null && buffer.getComponent(target, companionType) != null) {
            return true;
        }

        var ownerType = TameworkOwnerComponent.getComponentType();
        var owner = ownerType == null ? null : buffer.getComponent(target, ownerType);
        var tamedType = TameworkTamedComponent.getComponentType();
        var tamed = tamedType == null ? null : buffer.getComponent(target, tamedType);
        return (owner != null && owner.hasOwner()) || (tamed != null && tamed.isTamed());
    }
}
