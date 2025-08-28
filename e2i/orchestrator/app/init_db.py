from app.db import Base, engine
import app.models  # ensures models are registered

print("Creating tables...")
Base.metadata.create_all(bind=engine)
print("Done.")
