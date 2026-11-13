import java.io.InputStream;
import java.lang.classfile.ClassBuilder;
import java.lang.classfile.ClassFile;
import java.lang.classfile.ClassModel;
import java.lang.classfile.ClassTransform;
import java.lang.classfile.CodeElement;
import java.lang.classfile.CodeTransform;
import java.lang.classfile.Label;
import java.lang.classfile.instruction.InvokeInstruction;
import java.lang.constant.ClassDesc;
import java.lang.constant.MethodTypeDesc;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.Map;
import java.util.Set;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;
import java.util.zip.ZipOutputStream;

/** Local ownership guards layered on the already verified planting compatibility fix. */
public final class FixSeasonOwnership {
    private static final String INPUT_SHA256 = "9DB14EAF0C2B6B624152FAF27A7111F8D90820632433AB8B3989F4272277FD82";
    private static final ClassDesc STORE = ClassDesc.of("com.hypixel.hytale.component.Store");
    private static final ClassDesc REF = ClassDesc.of("com.hypixel.hytale.component.Ref");
    private static final ClassDesc TYPE = ClassDesc.of("com.hypixel.hytale.component.ComponentType");
    private static final ClassDesc COMPONENT = ClassDesc.of("com.hypixel.hytale.component.Component");
    private static final MethodTypeDesc ORIGINAL = MethodTypeDesc.of(COMPONENT, REF, TYPE);
    private static final MethodTypeDesc GUARDED = MethodTypeDesc.of(COMPONENT, STORE, REF, TYPE);
    private static final String HELPER = "localGetOwnedComponent";
    private static final Map<String, Set<String>> TARGETS = Map.of(
        "DynamicSeasons/SeasonPlugin", Set.of("lambda$startSeasonHeartbeats$2", "lambda$startSeasonHeartbeats$3", "lambda$refreshSeasonHUD$0"),
        "DynamicSeasons/system/SeasonWeatherSystem", Set.of("applyPlayerWeather")
    );

    public static void main(String[] arguments) throws Exception {
        if (arguments.length != 2) throw new IllegalArgumentException("Expected input and output JAR.");
        Path input = Path.of(arguments[0]);
        Path output = Path.of(arguments[1]);
        String hash = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(input)));
        if (!hash.equalsIgnoreCase(INPUT_SHA256)) throw new IllegalArgumentException("Input must contain the verified planting fix.");
        if (Files.exists(output)) throw new IllegalArgumentException("Output exists.");

        try (ZipFile source = new ZipFile(input.toFile()); ZipOutputStream result = new ZipOutputStream(Files.newOutputStream(output))) {
            int modified = 0;
            var entries = source.entries();
            while (entries.hasMoreElements()) {
                ZipEntry entry = entries.nextElement();
                byte[] contents;
                try (InputStream stream = source.getInputStream(entry)) { contents = stream.readAllBytes(); }
                String className = entry.getName().replaceFirst("\\.class$", "");
                if (TARGETS.containsKey(className)) {
                    contents = transform(contents, className, TARGETS.get(className));
                    modified++;
                }
                ZipEntry copy = new ZipEntry(entry.getName());
                copy.setTime(entry.getTime());
                if (entry.getComment() != null) copy.setComment(entry.getComment());
                if (entry.getExtra() != null) copy.setExtra(entry.getExtra());
                result.putNextEntry(copy);
                result.write(contents);
                result.closeEntry();
            }
            if (modified != 2) throw new IllegalStateException("Expected exactly two guarded classes.");
        }
    }

    private static byte[] transform(byte[] contents, String name, Set<String> methods) {
        ClassFile classFile = ClassFile.of();
        ClassModel model = classFile.parse(contents);
        ClassDesc owner = ClassDesc.ofInternalName(name);
        int[] calls = { 0 };
        ClassTransform replaceCalls = ClassTransform.transformingMethodBodies(
            method -> methods.contains(method.methodName().stringValue()),
            (builder, element) -> {
                if (element instanceof InvokeInstruction call && call.owner().asSymbol().equals(STORE) &&
                    call.name().equalsString("getComponent") && call.typeSymbol().equals(ORIGINAL)) {
                    builder.invokestatic(owner, HELPER, GUARDED);
                    calls[0]++;
                } else builder.with(element);
            });
        ClassTransform addGuard = new ClassTransform() {
            @Override public void accept(ClassBuilder builder, java.lang.classfile.ClassElement element) { builder.with(element); }
            @Override public void atEnd(ClassBuilder builder) {
                builder.withMethod(HELPER, GUARDED, ClassFile.ACC_PRIVATE | ClassFile.ACC_STATIC, method -> method.withCode(code -> {
                    Label absent = code.newLabel();
                    code.aload(1).ifnull(absent)
                        .aload(1).invokevirtual(REF, "getStore", MethodTypeDesc.of(STORE)).aload(0).if_acmpne(absent)
                        .aload(1).invokevirtual(REF, "isValid", MethodTypeDesc.of(ClassDesc.ofDescriptor("Z"))).ifeq(absent)
                        .aload(0).aload(1).aload(2).invokevirtual(STORE, "getComponent", ORIGINAL).areturn()
                        .labelBinding(absent).aconst_null().areturn();
                }));
            }
        };
        byte[] transformed = classFile.transformClass(model, replaceCalls.andThen(addGuard));
        int expected = name.equals("DynamicSeasons/SeasonPlugin") ? 9 : 1;
        if (calls[0] != expected) throw new IllegalStateException("Unexpected lookup coverage in " + name + ": " + calls[0]);
        if (!classFile.verify(transformed).isEmpty()) throw new IllegalStateException("Invalid transformed class " + name);
        System.out.println(name + " guarded lookups=" + calls[0]);
        return transformed;
    }
}
