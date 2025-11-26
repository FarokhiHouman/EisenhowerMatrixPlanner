// Services/EfTaskRepository.cs
using EisenhowerMatrixPlanner.Core.Entities;
using EisenhowerMatrixPlanner.Core.Interfaces;

using Microsoft.EntityFrameworkCore;


namespace EisenhowerMatrixPlanner.Services;
public class EfTaskRepository : ITaskRepository {
	public EfTaskRepository(AppDbContext context) => _context = context;
	private readonly AppDbContext                _context;
	public async     Task<IEnumerable<TaskItem>> GetAllAsync()         => await _context.Tasks.ToListAsync();
	public async     Task<TaskItem?>             GetByIdAsync(Guid id) => await _context.Tasks.FindAsync(id);

	public async Task AddAsync(TaskItem task) {
		await _context.Tasks.AddAsync(task);
		await _context.SaveChangesAsync();
	}

	public async Task UpdateAsync(TaskItem task) {
		_context.Tasks.Update(task);
		await _context.SaveChangesAsync();
	}

	public async Task DeleteAsync(Guid id) {
		TaskItem? task = await _context.Tasks.FindAsync(id);
		if (task != null) {
			_context.Tasks.Remove(task);
			await _context.SaveChangesAsync();
		}
	}
}