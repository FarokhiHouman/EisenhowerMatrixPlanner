// App.xaml.cs
using System.Windows;

using EisenhowerMatrixPlanner.Core.Entities;
using EisenhowerMatrixPlanner.Core.Interfaces;
using EisenhowerMatrixPlanner.Services;
using EisenhowerMatrixPlanner.ViewModels;

using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;


namespace EisenhowerMatrixPlanner;
public partial class App : Application {
	public static IServiceProvider ServiceProvider { get; private set; } = null!;

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

		// SQLite
		services.AddDbContext<AppDbContext>(options => options.UseSqlite("Data Source=tasks.db"));
		services.AddScoped<ITaskRepository, EfTaskRepository>();
		services.AddSingleton<TaskService>();
		services.AddSingleton<MainWindowViewModel>();
		services.AddTransient<MainWindow>();
	}
}