// Services/TaskService.cs
using EisenhowerMatrixPlanner.Core.Entities;
using EisenhowerMatrixPlanner.Core.Interfaces;


namespace EisenhowerMatrixPlanner.Services;
public class TaskService {
	public TaskService(ITaskRepository repository) => _repository = repository;
	private readonly ITaskRepository             _repository;
	public async     Task<IEnumerable<TaskItem>> GetAllTasksAsync()             => await _repository.GetAllAsync();
	public async     Task                        AddTaskAsync(TaskItem    task) => await _repository.AddAsync(task);
	public async     Task                        UpdateTaskAsync(TaskItem task) => await _repository.UpdateAsync(task);
	public async     Task                        DeleteTaskAsync(Guid     id)   => await _repository.DeleteAsync(id);

	// محاسبه موقعیت روی Canvas (10×10 grid)
	public void UpdateCanvasPosition(TaskItem task, double canvasWidth, double canvasHeight) {
		const int    gridSize   = 10;
		const double margin     = 60; // فاصله از لبه‌ها + فضای هدر
		double       cellWidth  = (canvasWidth  - 2 * margin) / gridSize;
		double       cellHeight = (canvasHeight - 2 * margin) / gridSize;

		// Urgency = چپ به راست (1 تا 10)
		// Importance = پایین به بالا (1 تا 10) → چون Y در WPF از بالا شروع میشه
		task.CanvasX = margin + (task.Urgency - 1) * cellWidth + cellWidth / 2 - 85; // 85 = نصف عرض کارت (170/2)
		task.CanvasY =
			canvasHeight - margin - (task.Importance - 1) * cellHeight - cellHeight / 2 - 55; // 55 = نصف ارتفاع کارت
	}
}