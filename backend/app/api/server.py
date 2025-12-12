from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import sqlite3
from datetime import datetime
import uuid
import os

# Create router instead of app
router = APIRouter()

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'binaapp.db')

# Database setup
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id TEXT PRIMARY KEY,
                  email TEXT UNIQUE NOT NULL,
                  name TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Projects table
    c.execute('''CREATE TABLE IF NOT EXISTS projects
                 (id TEXT PRIMARY KEY,
                  user_id TEXT NOT NULL,
                  name TEXT NOT NULL,
                  description TEXT,
                  template TEXT,
                  status TEXT DEFAULT 'draft',
                  html_content TEXT,
                  published_url TEXT,
                  views INTEGER DEFAULT 0,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (user_id) REFERENCES users(id))''')
    
    conn.commit()
    conn.close()

init_db()

# Database helper
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Models
class User(BaseModel):
    email: str
    name: Optional[str] = None

class Project(BaseModel):
    name: str
    description: Optional[str] = None
    template: Optional[str] = "blank"

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    html_content: Optional[str] = None
    status: Optional[str] = None

# API Endpoints
@router.post("/users")
async def create_user(user: User):
    conn = get_db()
    c = conn.cursor()
    
    user_id = str(uuid.uuid4())
    
    try:
        c.execute("INSERT INTO users (id, email, name) VALUES (?, ?, ?)",
                  (user_id, user.email, user.name))
        conn.commit()
        return {"id": user_id, "email": user.email, "name": user.name}
    except sqlite3.IntegrityError:
        c.execute("SELECT * FROM users WHERE email = ?", (user.email,))
        row = c.fetchone()
        return {"id": row['id'], "email": row['email'], "name": row['name']}
    finally:
        conn.close()

@router.get("/users/{user_id}/projects")
async def get_user_projects(user_id: str):
    conn = get_db()
    c = conn.cursor()
    
    c.execute("""SELECT * FROM projects 
                 WHERE user_id = ? 
                 ORDER BY updated_at DESC""", (user_id,))
    
    projects = []
    for row in c.fetchall():
        projects.append({
            "id": row['id'],
            "name": row['name'],
            "description": row['description'],
            "template": row['template'],
            "status": row['status'],
            "published_url": row['published_url'],
            "views": row['views'],
            "created_at": row['created_at'],
            "updated_at": row['updated_at']
        })
    
    conn.close()
    return {"projects": projects}

@router.post("/users/{user_id}/projects")
async def create_project(user_id: str, project: Project):
    conn = get_db()
    c = conn.cursor()
    
    project_id = str(uuid.uuid4())
    
    html_content = f"<html><body><h1>{project.name}</h1></body></html>"
    
    c.execute("""INSERT INTO projects 
                 (id, user_id, name, description, template, html_content) 
                 VALUES (?, ?, ?, ?, ?, ?)""",
              (project_id, user_id, project.name, project.description, 
               project.template, html_content))
    
    conn.commit()
    conn.close()
    
    return {
        "id": project_id,
        "name": project.name,
        "description": project.description,
        "template": project.template,
        "status": "draft"
    }

@router.get("/projects/{project_id}")
async def get_project(project_id: str):
    conn = get_db()
    c = conn.cursor()
    
    c.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
    row = c.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")
    
    conn.close()
    
    return {
        "id": row['id'],
        "user_id": row['user_id'],
        "name": row['name'],
        "description": row['description'],
        "template": row['template'],
        "status": row['status'],
        "html_content": row['html_content'],
        "published_url": row['published_url'],
        "views": row['views'],
        "created_at": row['created_at'],
        "updated_at": row['updated_at']
    }

@router.put("/projects/{project_id}")
async def update_project(project_id: str, update: ProjectUpdate):
    conn = get_db()
    c = conn.cursor()
    
    updates = []
    values = []
    
    if update.name:
        updates.append("name = ?")
        values.append(update.name)
    if update.description is not None:
        updates.append("description = ?")
        values.append(update.description)
    if update.html_content is not None:
        updates.append("html_content = ?")
        values.append(update.html_content)
    if update.status:
        updates.append("status = ?")
        values.append(update.status)
        if update.status == "published":
            published_url = f"https://preview.binaapp.my/{project_id}"
            updates.append("published_url = ?")
            values.append(published_url)
    
    updates.append("updated_at = ?")
    values.append(datetime.now().isoformat())
    
    values.append(project_id)
    
    query = f"UPDATE projects SET {', '.join(updates)} WHERE id = ?"
    c.execute(query, values)
    
    conn.commit()
    conn.close()
    
    return {"message": "Project updated successfully"}

@router.delete("/projects/{project_id}")
async def delete_project(project_id: str):
    conn = get_db()
    c = conn.cursor()
    
    c.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    
    if c.rowcount == 0:
        raise HTTPException(status_code=404, detail="Project not found")
    
    conn.commit()
    conn.close()
    
    return {"message": "Project deleted successfully"}

@router.get("/stats/{user_id}")
async def get_user_stats(user_id: str):
    conn = get_db()
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) as total FROM projects WHERE user_id = ?", (user_id,))
    total = c.fetchone()['total']
    
    c.execute("SELECT COUNT(*) as published FROM projects WHERE user_id = ? AND status = 'published'", (user_id,))
    published = c.fetchone()['published']
    
    c.execute("SELECT SUM(views) as total_views FROM projects WHERE user_id = ?", (user_id,))
    views_row = c.fetchone()
    total_views = views_row['total_views'] if views_row['total_views'] else 0
    
    conn.close()
    
    return {
        "total_websites": total,
        "published": published,
        "total_views": total_views
    }