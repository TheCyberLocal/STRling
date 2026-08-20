import org.gradle.api.publish.maven.MavenPublication

plugins {
    kotlin("jvm") version "2.0.20"
    `java-library`
    id("maven-publish")
}

group = "com.strling"
version = providers.gradleProperty("version").orElse("3.0.0").get()

repositories {
    providers.environmentVariable("STRLING_MAVEN_REPOSITORY").orNull?.let {
        maven { url = uri(it) }
    }
    mavenLocal()
    mavenCentral()
}

dependencies {
    api("com.strling:strling-jvm:3.0.0")
    testImplementation(kotlin("test"))
}

tasks.test {
    useJUnitPlatform()
    testLogging {
        events("passed", "skipped", "failed")
        showStandardStreams = true
        exceptionFormat = org.gradle.api.tasks.testing.logging.TestExceptionFormat.FULL
    }
    addTestListener(object : org.gradle.api.tasks.testing.TestListener {
        override fun beforeSuite(suite: org.gradle.api.tasks.testing.TestDescriptor) {}
        override fun afterSuite(suite: org.gradle.api.tasks.testing.TestDescriptor, result: org.gradle.api.tasks.testing.TestResult) {
            if (suite.parent == null) {
                println("[STRling Audit] Tests: ${result.testCount}, Skipped: ${result.skippedTestCount}")
            }
        }
        override fun beforeTest(testDescriptor: org.gradle.api.tasks.testing.TestDescriptor) {}
        override fun afterTest(testDescriptor: org.gradle.api.tasks.testing.TestDescriptor, result: org.gradle.api.tasks.testing.TestResult) {}
    })
}

kotlin {
    compilerOptions {
        allWarningsAsErrors = true
    }
}

publishing {
    repositories {
        providers.environmentVariable("STRLING_LOCAL_MAVEN_REPOSITORY").orNull?.let {
            maven {
                name = "localInstall"
                url = uri(it)
            }
        }
    }
    publications {
        create<MavenPublication>("maven") {
            from(components["java"])
        }
    }
}
