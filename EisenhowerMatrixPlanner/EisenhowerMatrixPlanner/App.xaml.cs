// App.xaml.cs
using System.Windows;

using EisenhowerMatrixPlanner.Core.Interfaces;
using EisenhowerMatrixPlanner.Services;
using EisenhowerMatrixPlanner.ViewModels;

using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;


namespace EisenhowerMatrixPlanner;
public partial class App : Application {
	public static IServiceProvider ServiceProvider { get; private set; }

	protected override void OnStartup(StartupEventArgs e) {
		base.OnStartup(e);
		ServiceCollection services = new();
		ConfigureServices(services);
		ServiceProvider = services.BuildServiceProvider();
		MainWindow mainWindow = ServiceProvider.GetRequiredService<MainWindow>();
		mainWindow.Show();
	}

	private void ConfigureServices(ServiceCollection services) {
		services.AddLogging(builder => builder.AddDebug());

		// Repository & Services
		services.AddSingleton<ITaskRepository, InMemoryTaskRepository>();
		services.AddSingleton<TaskService>();

		// ViewModels
		services.AddSingleton<MainWindowViewModel>();

		// Windows
		services.AddTransient<MainWindow>();
	}
}