// scripts/mongo_init_edumatch_resource.js
//
// Creates the EduMatch Resource Mapping database, its collections,
// and basic indexes.
//
// Usage:
//   mongosh "<ATLAS_CONNECTION_STRING>" scripts/mongo_init_edumatch_resource.js
//
// Idempotent: createCollection is wrapped so re-runs do not fail if a
// collection already exists; createIndex is a no-op when the index exists.

const dbName = "edumatch_resource_db";
const targetDb = db.getSiblingDB(dbName);

const collections = [
  "users",
  "courses",
  "course_resources",
  "student_profiles",
  "recommendations",
  "processing_logs",
  // Optional — uncomment to enable long-document chunking:
  // "resource_chunks",
];

function ensureCollection(name) {
  const existing = targetDb.getCollectionNames();
  if (existing.includes(name)) {
    print(`Collection already exists: ${name}`);
    return;
  }
  targetDb.createCollection(name);
  print(`Created collection: ${name}`);
}

collections.forEach(ensureCollection);

// --- users ---
targetDb.users.createIndex({ email: 1 }, { unique: true });
targetDb.users.createIndex({ role: 1 });

// --- courses ---
targetDb.courses.createIndex({ teacher_id: 1 });
targetDb.courses.createIndex({ level: 1 });
targetDb.courses.createIndex({ status: 1 });
targetDb.courses.createIndex({ manual_tags: 1 });
targetDb.courses.createIndex({ extracted_skills: 1 });
targetDb.courses.createIndex({ title: "text", description: "text" });

// --- course_resources ---
targetDb.course_resources.createIndex({ course_id: 1 });
targetDb.course_resources.createIndex({ uploaded_by: 1 });
targetDb.course_resources.createIndex({ processing_status: 1 });
targetDb.course_resources.createIndex({ file_type: 1 });
targetDb.course_resources.createIndex({ extracted_skills: 1 });

// --- student_profiles ---
targetDb.student_profiles.createIndex({ student_id: 1 });
targetDb.student_profiles.createIndex({ current_level: 1 });
targetDb.student_profiles.createIndex({ desired_skills: 1 });
targetDb.student_profiles.createIndex({ career_goal: 1 });

// --- recommendations ---
targetDb.recommendations.createIndex({ student_id: 1 });
targetDb.recommendations.createIndex({ student_profile_id: 1 });
targetDb.recommendations.createIndex({ created_at: -1 });

// --- processing_logs ---
targetDb.processing_logs.createIndex({ resource_id: 1 });
targetDb.processing_logs.createIndex({ course_id: 1 });
targetDb.processing_logs.createIndex({ created_at: -1 });
targetDb.processing_logs.createIndex({ status: 1 });

// --- resource_chunks (optional) ---
// targetDb.resource_chunks.createIndex({ resource_id: 1 });
// targetDb.resource_chunks.createIndex({ course_id: 1 });
// targetDb.resource_chunks.createIndex({ chunk_index: 1 });

print(`Database ${dbName} initialized successfully.`);
