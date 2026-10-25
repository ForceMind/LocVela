plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}
android {
    namespace = "app.locvela.controller"
    compileSdk = 36
    buildToolsVersion = "35.0.0"
    defaultConfig {
        applicationId = "app.locvela.controller"
        minSdk = 31
        targetSdk = 36
        versionCode = 2
        versionName = "0.1.0-alpha.1"
    }
    buildFeatures { compose = true; buildConfig = true }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    lint { abortOnError = true }
    packaging { resources.merges += "/META-INF/{AL2.0,LGPL2.1}" }
    sourceSets.getByName("main").assets.srcDir(layout.buildDirectory.dir("generated/legalAssets"))
}
val copyLegalNotices by tasks.registering(Sync::class) {
    from(rootProject.file("../..")) { include("LICENSE", "COPYRIGHT", "THIRD_PARTY_NOTICES.md") }
    into(layout.buildDirectory.dir("generated/legalAssets/legal"))
}
tasks.named("preBuild") { dependsOn(copyLegalNotices) }
kotlin { jvmToolchain(17) }
dependencies {
    implementation(project(":model"))
    implementation(platform("androidx.compose:compose-bom:2025.08.01"))
    implementation("androidx.activity:activity-compose:1.10.1")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.foundation:foundation")
    implementation("androidx.core:core-ktx:1.16.0")
}
