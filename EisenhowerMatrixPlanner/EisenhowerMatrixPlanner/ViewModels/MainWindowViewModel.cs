// ViewModels/MainWindowViewModel.cs
using System.Collections.ObjectModel;

using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

using EisenhowerMatrixPlanner.Core.Entities;
using EisenhowerMatrixPlanner.Services;


namespace EisenhowerMatrixPlanner.ViewModels; // این خط حیاتیه!
public partial class MainWindowViewModel : ObservableObject {
	public MainWindowViewModel(TaskService taskService) {
		_taskService     = taskService;
		LoadTasksCommand = new AsyncRelayCommand(LoadTasksAsync);
		AddTaskCommand   = new RelayCommand(AddTask);

		// لود اولیه
		_ = LoadTasksAsync();
	}

	public ObservableCollection<TaskItem> Tasks            { get; } = new();
	public IAsyncRelayCommand             LoadTasksCommand { get; }
	public IRelayCommand                  AddTaskCommand   { get; }
	[ObservableProperty]
	private string _title = "Eisenhower Matrix Planner";
	private readonly TaskService _taskService;

	private async Task LoadTasksAsync() {
		Tasks.Clear();
		IEnumerable<TaskItem> tasks = await _taskService.GetAllTasksAsync();
		foreach (TaskItem task in tasks) {
			Tasks.Add(task);
			_taskService.UpdateCanvasPosition(task, canvasWidth: 900, canvasHeight: 550);
		}
	}

	private async void AddTask() {
		TaskItem newTask = new("New Task", importance: 5, urgency: 5);
		Tasks.Add(newTask);
		_taskService.UpdateCanvasPosition(newTask, canvasWidth: 900, canvasHeight: 550);
		await _taskService.AddTaskAsync(newTask);
	}
}