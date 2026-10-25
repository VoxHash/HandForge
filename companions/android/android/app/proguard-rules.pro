# HandForge Companion — keep WebView bridge symbols if minify is enabled later.
-keepclassmembers class * {
    @android.webkit.JavascriptInterface <methods>;
}
