package steven.rangersnipers;

import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.client.ChargingInteraction;
import com.hypixel.hytale.protocol.*;
import com.hypixel.hytale.server.core.entity.InteractionContext;
import com.hypixel.hytale.server.core.inventory.*;
import com.hypixel.hytale.server.core.modules.interaction.interaction.CooldownHandler;
import org.bson.BsonDocument;

/** Native held aiming without declaring a defensive wield/block interaction.
 * Wielding's packet type and currentWielding state survive displayProgress=false.
 * Plain charging retains held input, zoom, movement and cancellation effects.
 */
public final class AimInteraction extends ChargingInteraction {
    public static final BuilderCodec<AimInteraction> CODEC = BuilderCodec
        .builder(AimInteraction.class, AimInteraction::new, ChargingInteraction.CODEC)
        .build();

    public AimInteraction() {
        displayProgress = false;
        allowIndefiniteHold = true;
        // Native Cancel compares the full BSON metadata, including loaded rounds.
        // Ignore that broad check; the guards below retain actual item identity.
        onItemChangeBehavior = InteractionItemChangeBehavior.Ignore;
    }

    @Override protected void tick0(boolean first,float time,InteractionType type,InteractionContext context,CooldownHandler cooldown) {
        if(refreshSameWeapon(context))super.tick0(first,time,type,context,cooldown);
    }
    @Override protected void simulateTick0(boolean first,float time,InteractionType type,InteractionContext context,CooldownHandler cooldown) {
        if(refreshSameWeapon(context))super.simulateTick0(first,time,type,context,cooldown);
    }
    private static boolean refreshSameWeapon(InteractionContext context) {
        try {
            var commands=context.getCommandBuffer();var owner=context.getOwningEntity();
            if(commands==null||owner==null||!owner.isValid()||context.getHeldItemSectionId()!=InventoryComponent.HOTBAR_SECTION_ID)return fail(context);
            var hotbar=commands.getComponent(owner,InventoryComponent.Hotbar.getComponentType());
            var container=context.getHeldItemContainer();short slot=context.getHeldItemSlot();
            if(hotbar==null||hotbar.getInventory()!=container||hotbar.getActiveSlot()!=slot)return fail(context);
            var old=context.getHeldItem();var actual=container.getItemStack(slot);
            if(old==null||actual==null||old.getQuantity()!=1||actual.getQuantity()!=1||!old.getItemId().equals(actual.getItemId()))return fail(context);
            var profile=RangerSnipersPlugin.PROFILES.get(old.getItemId());
            if(profile==null)return fail(context);
            // Fresh empty receivers have no instance yet; unchanged native
            // equivalent stacks remain aimable until Use initializes a chamber.
            if(!old.isEquivalentType(actual)) {
                var before=ChamberState.read(old,profile);var after=ChamberState.read(actual,profile);
                if(before.instanceId()==null||!before.instanceId().equals(after.instanceId())||after.revision()<=before.revision())return fail(context);
                BsonDocument oldMeta=old.getMetadata().clone(),newMeta=actual.getMetadata().clone();
                BsonDocument oldChamber=oldMeta.remove(ChamberState.KEY).asDocument().clone();
                BsonDocument newChamber=newMeta.remove(ChamberState.KEY).asDocument().clone();
                oldChamber.remove("Loaded");oldChamber.remove("Revision");newChamber.remove("Loaded");newChamber.remove("Revision");
                if(!oldMeta.equals(newMeta)||!oldChamber.equals(newChamber))return fail(context);
            }
            context.setHeldItem(actual);return true;
        } catch(RuntimeException rejected) {return fail(context);}
    }
    private static boolean fail(InteractionContext context){context.getState().state=InteractionState.Failed;return false;}
}
