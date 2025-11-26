// Core/Interfaces/ITaskRepository.cs
using EisenhowerMatrixPlanner.Core.Entities;


namespace EisenhowerMatrixPlanner.Core.Interfaces;
public interface ITaskRepository {
	Task<IEnumerable<TaskItem>> GetAllAsync();
	Task<TaskItem>              GetByIdAsync(Guid    id);
	Task                        AddAsync(TaskItem    task);
	Task                        UpdateAsync(TaskItem task);
	Task                        DeleteAsync(Guid     id);
}