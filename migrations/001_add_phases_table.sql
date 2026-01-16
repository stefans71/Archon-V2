-- Migration: Add phases table and phase_id to tasks
-- Purpose: Enable phase-based project lifecycle management
-- Run this in Supabase SQL editor

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create phases table
CREATE TABLE IF NOT EXISTS archon_phases (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES archon_projects(id) ON DELETE CASCADE,
    phase_number INTEGER NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'planning' CHECK (status IN ('planning', 'active', 'complete')),
    summary TEXT,  -- Written at phase end by AI
    goals JSONB DEFAULT '[]'::jsonb,  -- Phase goals
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Ensure unique phase numbers per project
    CONSTRAINT unique_phase_number_per_project UNIQUE (project_id, phase_number)
);

-- Add index for common queries
CREATE INDEX IF NOT EXISTS idx_archon_phases_project_id ON archon_phases(project_id);
CREATE INDEX IF NOT EXISTS idx_archon_phases_status ON archon_phases(status);

-- Add phase_id to tasks table
ALTER TABLE archon_tasks
ADD COLUMN IF NOT EXISTS phase_id UUID REFERENCES archon_phases(id) ON DELETE SET NULL;

-- Add index for phase-based task queries
CREATE INDEX IF NOT EXISTS idx_archon_tasks_phase_id ON archon_tasks(phase_id);

-- Add RLS policies (if using Row Level Security)
-- Note: Adjust these based on your RLS setup

-- Enable RLS on phases table
ALTER TABLE archon_phases ENABLE ROW LEVEL SECURITY;

-- Allow all operations for authenticated users (adjust as needed)
CREATE POLICY "Allow all operations on phases"
    ON archon_phases
    FOR ALL
    USING (true)
    WITH CHECK (true);

-- Grant permissions to service role
GRANT ALL ON archon_phases TO service_role;
GRANT ALL ON archon_phases TO authenticated;

-- Add comment to document the table
COMMENT ON TABLE archon_phases IS 'Project phases for lifecycle management. Each phase groups related tasks.';
COMMENT ON COLUMN archon_phases.status IS 'Phase status: planning (not started), active (in progress), complete (finished)';
COMMENT ON COLUMN archon_phases.summary IS 'AI-generated summary written when phase is completed';
COMMENT ON COLUMN archon_phases.goals IS 'JSON array of phase goals for tracking completion';
