# EyeSpy Container Preview Fix

Prevents unsupported quality overrides from reaching EyeSpy’s temporary container-preview UI. The displayed preview falls back to the item’s default quality.

Run the original transform with JDK 25 and your own copy of the exact reviewed EyeSpy `2026.10.30-21549` JAR. Use a new output path.

```powershell
java -cp 'PATH_TO_ORIGINAL_JAR;PATH_TO_SERVER_JAR' FixEyeSpyContainerQuality.java PATH_TO_ORIGINAL_JAR PATH_TO_OUTPUT_JAR
```

The transform checks the input fingerprint. The EyeSpy archive is an external input.
