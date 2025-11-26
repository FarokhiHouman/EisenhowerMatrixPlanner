// ViewModels/MainWindowViewModel.cs
using System.Collections.ObjectModel;

using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

using EisenhowerMatrixPlanner.Core.Entities;
using EisenhowerMatrixPlanner.Services;


namespace EisenhowerMatrixPlanner.ViewModels;
public partial class MainWindowViewModel : ObservableObject {
	public MainWindowViewModel(TaskService taskService) {
		_taskService = taskService;
		LoadSampleData();
	}

	public ObservableCollection<TaskItem> Tasks { get; } = new();
	[ObservableProperty]
	private string _title = "Eisenhower Matrix Planner";
	private readonly TaskService _taskService;

	private void LoadSampleData() {
		TaskItem t1 = new("پروژه نهایی", importance: 9, urgency: 9);
		TaskItem t2 = new("ورزش امروز", importance: 8, urgency: 6);
		TaskItem t3 = new("چک کردن اینستاگرام", importance: 2, urgency: 7);
		TaskItem t4 = new("یادگیری WPF", importance: 9, urgency: 3);
		Tasks.Add(t1);
		Tasks.Add(t2);
		Tasks.Add(t3);
		Tasks.Add(t4);
		foreach (TaskItem task in Tasks) {
			_taskService.UpdateCanvasPosition(task,
											  canvasWidth: 900,
											  canvasHeight: 550); // اندازه واقعی بعداً از Canvas می‌گیریم
		}
	}

	[RelayCommand]
	private void AddTask() {
		TaskItem newTask = new("تسک جدید", importance: 5, urgency: 5);
		Tasks.Add(newTask);
		_taskService.UpdateCanvasPosition(newTask, canvasWidth: 900, canvasHeight: 550);
	}
}