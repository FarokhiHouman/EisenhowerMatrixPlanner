// MainWindow.xaml.cs — نسخه درست و تمیز
using System.Windows;

using EisenhowerMatrixPlanner.Core.Entities;
using EisenhowerMatrixPlanner.Services;
using EisenhowerMatrixPlanner.ViewModels;


namespace EisenhowerMatrixPlanner;
public partial class MainWindow : Window {
	public MainWindow(MainWindowViewModel viewModel, TaskService taskService) {
		InitializeComponent();
		DataContext  = viewModel;
		_taskService = taskService;
	}

	private readonly TaskService _taskService; // کش می‌کنیم که هر بار نریم دنبالش

	private void MatrixCanvas_SizeChanged(object sender, SizeChangedEventArgs e) {
		if (DataContext is MainWindowViewModel vm) {
			foreach (TaskItem task in vm.Tasks) {
				_taskService.UpdateCanvasPosition(task, e.NewSize.Width, e.NewSize.Height);
			}
		}
	}
}