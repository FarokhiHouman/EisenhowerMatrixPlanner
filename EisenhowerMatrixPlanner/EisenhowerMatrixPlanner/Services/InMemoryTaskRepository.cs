// Services/InMemoryTaskRepository.cs
using System.Collections.Concurrent;

using EisenhowerMatrixPlanner.Core.Entities;
using EisenhowerMatrixPlanner.Core.Interfaces;


namespace EisenhowerMatrixPlanner.Services;
public class InMemoryTaskRepository : ITaskRepository {
	private readonly ConcurrentBag<TaskItem> _tasks = new();
	public           Task<IEnumerable<TaskItem>> GetAllAsync() => Task.FromResult<IEnumerable<TaskItem>>(_tasks);
	public           Task<TaskItem> GetByIdAsync(Guid id) => Task.FromResult(_tasks.FirstOrDefault(t => t.Id == id)!);

	public Task AddAsync(TaskItem task) {
		_tasks.Add(task);
		return Task.CompletedTask;
	}

	public Task UpdateAsync(TaskItem task) =>
		// چون رفرنس هست، نیازی به کار اضافه نیست (در نسخه SQLite بعداً SaveChanges می‌زنیم)
		Task.CompletedTask;

	public Task DeleteAsync(Guid id) {
		TaskItem? task = _tasks.FirstOrDefault(t => t.Id == id);
		if (task != null)
			_tasks.ToList().Remove(task);
		return Task.CompletedTask;
	}
}