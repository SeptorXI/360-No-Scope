package steven.brotherhood;

import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.inventory.container.*;
import com.hypixel.hytale.server.core.inventory.container.filter.*;
import com.hypixel.fastutil.ints.Int2ObjectConcurrentHashMap;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.lang.reflect.InvocationTargetException;
import java.util.*;
import java.util.function.BooleanSupplier;
import java.util.function.Consumer;

/** Adds only an Assassin check for exact Brotherhood IDs, preserving the live native/mod filter.
 * The pinned server exposes a filter setter without a getter. Reflection reads that one private
 * filter table; restoration changes a slot only while its current filter is still our wrapper. */
public final class ArmorEquipGate implements AutoCloseable {
    private static final Set<String> IDS = new HashSet<>();
    static { for (var piece : AffinityRules.PIECES) IDS.add(piece.itemId()); }
    private record Entry(ItemContainer container, short slot, Int2ObjectConcurrentHashMap<SlotFilter> table, SlotFilter previous, Gate wrapper) {}
    private final List<Entry> entries = new ArrayList<>();
    private boolean closed;
    private static final class Gate implements SlotFilter {
        final SlotFilter previous; final BooleanSupplier primaryAssassin; final Consumer<String> rejected;
        volatile boolean active = true;
        Gate(SlotFilter previous, BooleanSupplier eligible, Consumer<String> rejected) {
            this.previous=previous; primaryAssassin=eligible; this.rejected=rejected;
        }
        @Override public boolean test(FilterActionType action, ItemContainer container, short slot, ItemStack stack) {
            if (previous != null && !previous.test(action,container,slot,stack)) return false;
            if (!active || !isBrotherhood(stack)) return true;
            var armor=stack.getItem().getArmor();
            boolean nativeSlot=armor != null && armor.getArmorSlot().getValue()==slot;
            boolean allowed=stack.getQuantity()==1 && nativeSlot && primaryAssassin.getAsBoolean();
            if (!allowed) rejected.accept("Crimson Brotherhood armor requires a primary Assassin class or its ascended path.");
            return allowed;
        }
    }
    public static boolean isBrotherhood(ItemStack stack) { return stack != null && !ItemStack.isEmpty(stack) && IDS.contains(stack.getItemId()); }
    @SuppressWarnings("unchecked")
    private static Int2ObjectConcurrentHashMap<SlotFilter> table(ItemContainer container) {
        Class<?> type = container instanceof SimpleItemContainer ? SimpleItemContainer.class :
            container instanceof DelegateItemContainer<?> ? DelegateItemContainer.class : null;
        if (type == null) throw new IllegalStateException("Unsupported armor container for safe Brotherhood class gate: " + container.getClass().getName());
        try {
            Field field=type.getDeclaredField("slotFilters");field.setAccessible(true);
            var all=(Map<FilterActionType,Int2ObjectConcurrentHashMap<SlotFilter>>)field.get(container);
            var current=all.get(FilterActionType.ADD);
            if(current==null) {
                // Force native creation of the ADD map without accepting or removing any items.
                container.setSlotFilter(FilterActionType.ADD,(short)0,SlotFilter.ALLOW);
                current=all.get(FilterActionType.ADD);
                current.remove(0);
            }
            return current;
        } catch (ReflectiveOperationException error) { throw new IllegalStateException("Pinned Hytale armor-filter API changed; Brotherhood equipment gate cannot initialize",error); }
    }
    public synchronized void bind(ItemContainer container, BooleanSupplier eligible, Consumer<String> rejected) {
        if (closed) throw new IllegalStateException("Armor class gate closed");
        if (container==null) return;
        var filters=table(container);
        for(var piece:AffinityRules.PIECES) {
            short slot=(short)com.hypixel.hytale.protocol.ItemArmorSlot.valueOf(piece.slot().name()).getValue();
            if(slot>=container.getCapacity())continue;
            SlotFilter current=filters.get((int)slot);
            boolean owned=entries.stream().anyMatch(row->row.container()==container && row.slot()==slot && row.wrapper()==current);
            if(owned)continue;
            var gate=new Gate(current,eligible,rejected);
            entries.add(new Entry(container,slot,filters,current,gate));
            container.setSlotFilter(FilterActionType.ADD,slot,gate);
        }
    }
    /** Native atomic moves preserve exact metadata and remove the source only after destination accepts it. */
    public static int evacuate(ItemContainer armor, ArmorReturnState pending) {
        if(armor==null)return 0;
        int moved=0;
        for(short slot=0;slot<armor.getCapacity();slot++) {
            var stack=armor.getItemStack(slot);
            if(!isBrotherhood(stack))continue;
            pending.ensureRoom(stack);
            // Only owned class-invalid gear moves to private escrow. Ignore a foreign REMOVE
            // prohibition for this mandatory safe return; leave that filter installed for ordinary UI use.
            var transaction=armor.moveItemStackFromSlot(slot,pending.inventory(),true,false);
            if(transaction.succeeded()) { moved++;pending.changed(); }
            else throw new IllegalStateException("Could not safely return invalid-class Brotherhood armor; original item preserved");
        }
        return moved;
    }
    private static void nativeLock(ItemContainer container,String method) {
        try {
            Method action=ItemContainer.class.getDeclaredMethod(method);action.setAccessible(true);action.invoke(container);
        } catch(ReflectiveOperationException error) {
            Throwable cause=error instanceof InvocationTargetException && error.getCause()!=null?error.getCause():error;
            throw new IllegalStateException("Pinned Hytale container locking API changed",cause);
        }
    }
    /** Insert into one empty destination slot before removing our private source. The native
     * whole-stack move removes its source before a foreign ADD filter can throw, so it is not
     * used here. Both containers remain write-locked; native calls are reentrant on these locks.
     * A foreign post-insert event exception is reconciled from the exact inserted item once. */
    public static int returnPending(ArmorReturnState pending,ItemContainer... destinations) {
        if(pending==null)return 0;
        int returned=0;RuntimeException failure=null;
        var source=pending.inventory();
        nativeLock(source,"lockForWrite");
        try {
            for(short slot=0;slot<source.getCapacity();slot++) {
                var held=source.getItemStack(slot);
                if(ItemStack.isEmpty(held))continue;
                for(var destination:destinations) {
                    if(destination==null || destination==source)continue;
                    boolean locked=false;
                    try {
                        nativeLock(destination,"lockForWrite");locked=true;
                        for(short target=0;target<destination.getCapacity() && !ItemStack.isEmpty(source.getItemStack(slot));target++) {
                            if(!ItemStack.isEmpty(destination.getItemStack(target)))continue;
                            var original=source.getItemStack(slot);var one=original.withQuantity(1);
                            RuntimeException insertionError=null;
                            try { destination.setItemStackForSlot(target,one); }
                            catch(RuntimeException error) { insertionError=error; }
                            var after=destination.getItemStack(target);
                            if(one.equals(after)) {
                                // Private unfiltered storage cannot invoke a foreign filter or listener.
                                var removed=source.removeItemStackFromSlot(slot,1,false,false);
                                if(!removed.succeeded())throw new IllegalStateException("Private Brotherhood source changed during locked return");
                                pending.changed();returned++;
                            }
                            if(insertionError!=null)throw insertionError;
                        }
                    } catch(RuntimeException error) { if(failure==null)failure=error; }
                    finally { if(locked)nativeLock(destination,"unlockForWrite"); }
                    if(ItemStack.isEmpty(source.getItemStack(slot)))break;
                }
            }
        } finally { nativeLock(source,"unlockForWrite"); }
        if(failure!=null)throw new IllegalStateException("A destination rejected safe Brotherhood return; untransferred pieces remain in persisted storage",failure);
        return returned;
    }
    @Override public synchronized void close() {
        if(closed)return;closed=true;
        for(var row:entries) {
            row.wrapper().active=false;
            if(row.table().get((int)row.slot())!=row.wrapper())continue;
            if(row.previous()==null)row.table().remove((int)row.slot());
            else row.container().setSlotFilter(FilterActionType.ADD,row.slot(),row.previous());
        }
        entries.clear();
    }
}
