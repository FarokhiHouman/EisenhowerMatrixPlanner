// Core/Entities/AppDbContext.cs
using Microsoft.EntityFrameworkCore;


namespace EisenhowerMatrixPlanner.Core.Entities;
public class AppDbContext : DbContext {
	public AppDbContext() : base(GetDesignTimeOptions()) { }

	private static DbContextOptions<AppDbContext> GetDesignTimeOptions() {
		DbContextOptionsBuilder<AppDbContext> optionsBuilder = new();
		optionsBuilder.UseSqlite("Data Source=tasks.db");
		return optionsBuilder.Options;
	}

	public DbSet<TaskItem> Tasks => Set<TaskItem>();

	public AppDbContext(DbContextOptions<AppDbContext> options) : base(options) {
		Database.Migrate(); // این بهترین روشه — همیشه آخرین مایگریشن رو اعمال می‌کنه
	}

	protected override void OnModelCreating(ModelBuilder modelBuilder) {
		modelBuilder.Entity<TaskItem>(entity => {
										  entity.HasKey(t => t.Id);
										  entity.Property(t => t.Title).IsRequired().HasMaxLength(200);
										  entity.Property(t => t.Description).HasMaxLength(1000);
									  });
	}
}