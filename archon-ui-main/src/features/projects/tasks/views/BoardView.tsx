import { ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";
import { KanbanColumn } from "../components/KanbanColumn";
import type { Task } from "../types";

interface BoardViewProps {
  tasks: Task[];
  projectId: string;
  onTaskMove: (taskId: string, newStatus: Task["status"]) => void;
  onTaskReorder: (taskId: string, targetIndex: number, status: Task["status"]) => void;
  onTaskEdit?: (task: Task) => void;
  onTaskDelete?: (task: Task) => void;
  maxDoneTasks?: number;
}

const DEFAULT_MAX_DONE_TASKS = 5;

export const BoardView = ({
  tasks,
  projectId,
  onTaskMove,
  onTaskReorder,
  onTaskEdit,
  onTaskDelete,
  maxDoneTasks = DEFAULT_MAX_DONE_TASKS,
}: BoardViewProps) => {
  const [hoveredTaskId, setHoveredTaskId] = useState<string | null>(null);
  const [showAllDone, setShowAllDone] = useState(false);

  // Get all done tasks sorted by updated_at (most recent first)
  const allDoneTasks = tasks
    .filter((task) => task.status === "done")
    .sort((a, b) => {
      // Sort by updated_at descending (most recent first)
      const dateA = a.updated_at ? new Date(a.updated_at).getTime() : 0;
      const dateB = b.updated_at ? new Date(b.updated_at).getTime() : 0;
      return dateB - dateA;
    });

  const totalDoneTasks = allDoneTasks.length;
  const hasMoreDoneTasks = totalDoneTasks > maxDoneTasks;

  // Simple task filtering for board view
  const getTasksByStatus = (status: Task["status"]) => {
    if (status === "done") {
      // For done column, show limited tasks unless "show all" is enabled
      if (showAllDone || !hasMoreDoneTasks) {
        return allDoneTasks;
      }
      return allDoneTasks.slice(0, maxDoneTasks);
    }
    return tasks.filter((task) => task.status === status).sort((a, b) => a.task_order - b.task_order);
  };

  // Column configuration
  const columns: Array<{ status: Task["status"]; title: string }> = [
    { status: "todo", title: "Todo" },
    { status: "doing", title: "Doing" },
    { status: "review", title: "Review" },
    { status: "done", title: `Done${hasMoreDoneTasks && !showAllDone ? ` (${maxDoneTasks}/${totalDoneTasks})` : totalDoneTasks > 0 ? ` (${totalDoneTasks})` : ""}` },
  ];

  // Toggle button for showing all done tasks
  const doneColumnFooter = hasMoreDoneTasks ? (
    <button
      type="button"
      onClick={() => setShowAllDone(!showAllDone)}
      className="w-full flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium text-green-600 dark:text-green-400 bg-green-500/10 hover:bg-green-500/20 border border-green-500/30 rounded-lg transition-colors"
    >
      {showAllDone ? (
        <>
          <ChevronUp className="w-3.5 h-3.5" />
          Show less
        </>
      ) : (
        <>
          <ChevronDown className="w-3.5 h-3.5" />
          Show all {totalDoneTasks} done tasks
        </>
      )}
    </button>
  ) : null;

  return (
    <div className="flex flex-col h-full min-h-[70vh] relative">
      {/* Board Columns Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-2 flex-1 p-2 min-h-[500px]">
        {columns.map(({ status, title }) => (
          <KanbanColumn
            key={status}
            status={status}
            title={title}
            tasks={getTasksByStatus(status)}
            projectId={projectId}
            onTaskMove={onTaskMove}
            onTaskReorder={onTaskReorder}
            onTaskEdit={onTaskEdit}
            onTaskDelete={onTaskDelete}
            hoveredTaskId={hoveredTaskId}
            onTaskHover={setHoveredTaskId}
            footerAction={status === "done" ? doneColumnFooter : undefined}
          />
        ))}
      </div>
    </div>
  );
};
