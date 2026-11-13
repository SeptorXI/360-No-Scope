import java.io.InputStream;
import java.lang.classfile.ClassFile;
import java.lang.classfile.ClassTransform;
import java.lang.classfile.instruction.InvokeInstruction;
import java.lang.constant.ClassDesc;
import java.lang.constant.ConstantDescs;
import java.lang.constant.MethodTypeDesc;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;
import java.util.zip.ZipOutputStream;

/** Remove server-only QualityOverride from EyeSpy's temporary container-preview stacks. */
public final class FixEyeSpyContainerQuality {
    private static final String EXPECTED_SHA256 = "536a94d6024e552efe3c196720aaa175db1eb3e30f6be59b35902f0d8e566e91";
    private static final String TARGET = "com/jarhax/eyespy/impl/info/VanillaBlockInfoProvider.class";
    private static final ClassDesc STACK = ClassDesc.of("com.hypixel.hytale.server.core.inventory.ItemStack");
    private static final MethodTypeDesc DURABILITY = MethodTypeDesc.of(STACK, ConstantDescs.CD_double);
    private static final MethodTypeDesc QUALITY = MethodTypeDesc.of(STACK, ConstantDescs.CD_int);

    public static void main(String[] args) throws Exception {
        if (args.length != 2) throw new IllegalArgumentException("Expected input and output JAR paths.");
        Path input = Path.of(args[0]);
        Path output = Path.of(args[1]);
        String hash = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(input)));
        if (!hash.equals(EXPECTED_SHA256)) throw new IllegalArgumentException("Input hash does not match the reviewed installed EyeSpy archive.");
        if (Files.exists(output)) throw new IllegalArgumentException("Output already exists.");
        try (ZipFile source = new ZipFile(input.toFile())) {
            for (var entry : source.stream().toList()) {
                String name = entry.getName().toUpperCase(java.util.Locale.ROOT);
                if ((name.startsWith("META-INF/") && (name.endsWith(".SF") || name.endsWith(".RSA") || name.endsWith(".DSA") || name.endsWith(".EC"))) ||
                        name.contains("RESOURCE-LEDGER") || name.contains("INTEGRITY")) {
                    throw new IllegalStateException("Archive has signature/integrity resources; refusing modification.");
                }
            }
            int changed = 0;
            try (ZipOutputStream result = new ZipOutputStream(Files.newOutputStream(output))) {
                var entries = source.entries();
                while (entries.hasMoreElements()) {
                    ZipEntry entry = entries.nextElement();
                    byte[] data;
                    try (InputStream in = source.getInputStream(entry)) { data = in.readAllBytes(); }
                    if (entry.getName().equals(TARGET)) { data = patch(data); changed++; }
                    ZipEntry copy = new ZipEntry(entry.getName());
                    copy.setTime(entry.getTime());
                    if (entry.getComment() != null) copy.setComment(entry.getComment());
                    if (entry.getExtra() != null) copy.setExtra(entry.getExtra());
                    result.putNextEntry(copy);
                    result.write(data);
                    result.closeEntry();
                }
            }
            if (changed != 1) throw new IllegalStateException("Expected exactly one target class.");
        }
        System.out.println("Patched one provider class; one temporary-stack normalization call inserted.");
    }

    private static byte[] patch(byte[] original) {
        ClassFile cf = ClassFile.of();
        int[] inserted = {0};
        ClassTransform transform = ClassTransform.transformingMethodBodies(
            method -> method.methodName().equalsString("getStacks"),
            (builder, element) -> {
                builder.with(element);
                if (element instanceof InvokeInstruction call && call.owner().asSymbol().equals(STACK) &&
                    call.name().equalsString("withDurability") && call.typeSymbol().equals(DURABILITY)) {
                    // Existing code already made the display copy and removed its metadata.
                    // MIN_VALUE is ItemStack's unset quality sentinel; its codec omits this field.
                    builder.loadConstant(Integer.MIN_VALUE).invokevirtual(STACK, "withQuality", QUALITY);
                    inserted[0]++;
                }
            });
        byte[] result = cf.transformClass(cf.parse(original), transform);
        if (inserted[0] != 1) throw new IllegalStateException("Expected one display-copy call site; found " + inserted[0]);
        if (!cf.verify(result).isEmpty()) throw new IllegalStateException("ClassFile verifier rejected output: " + cf.verify(result));
        return result;
    }
}
