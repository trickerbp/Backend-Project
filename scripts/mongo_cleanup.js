// scripts/mongo_cleanup.js
//
// Drops legacy/unrelated databases that are no longer part of the
// "EduMatch Resource Mapping" project scope.
//
// SYSTEM DATABASES ARE NEVER TOUCHED: admin, local, config.
//
// Usage:
//   mongosh "<ATLAS_CONNECTION_STRING>" scripts/mongo_cleanup.js
//
// sample_mflix is also dropped by default so the cluster only keeps
// project data plus MongoDB system databases.

const dbsToDrop = [
  "class_enroll_db",
  "edumatch_db",
  "learning_mapping_db",
  "student_db",
  "student_management",
];

// Hard guard: never drop MongoDB system databases.
const protectedDbs = ["admin", "local", "config"];

const includeSampleMflix = true;

print("=== MongoDB cleanup: EduMatch Resource Mapping ===");
print("Databases targeted for drop:");
dbsToDrop.forEach((name) => print(`  - ${name}`));
print("Protected (never dropped): " + protectedDbs.join(", "));
const projectDb = db.getSiblingDB('edumatch_resource_db');
const legacyCollections = ['classes', 'enrollments', 'learning_needs'];
legacyCollections.forEach((name) => {
  if (projectDb.getCollectionNames().includes(name)) {
    print(`Dropping legacy collection: ${name}`);
    projectDb.getCollection(name).drop();
  }
});

print("");

dbsToDrop.forEach((dbName) => {
  if (protectedDbs.includes(dbName)) {
    print(`SKIP (protected system database): ${dbName}`);
    return;
  }
  print(`Dropping database: ${dbName}`);
  const targetDb = db.getSiblingDB(dbName);
  const result = targetDb.dropDatabase();
  printjson(result);
});

if (includeSampleMflix) {
  print("Dropping sample database: sample_mflix");
  const result = db.getSiblingDB("sample_mflix").dropDatabase();
  printjson(result);
} else {
  print("Keeping sample_mflix because includeSampleMflix is false.");
}

print("");
print("Cleanup completed.");
