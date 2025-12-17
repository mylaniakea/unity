# Contributing to Unity

Thank you for your interest in contributing to Unity - the Homelab Intelligence Hub!

## Development Setup

See the [README.md](./README.md) for initial setup instructions.

## Development Workflow

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Follow existing code style
   - Add tests for new functionality
   - Update documentation as needed

3. **Test your changes**
   ```bash
   # Backend
   cd backend && pytest
   
   # Frontend
   cd frontend && npm test
   ```

4. **Commit with clear messages**
   ```bash
   git commit -m "Add: brief description of changes"
   ```

5. **Push and create a pull request**
   ```bash
   git push origin feature/your-feature-name
   ```

## Code Style

### Python (Backend)
- Follow PEP 8
- Use type hints
- Write docstrings for functions and classes
- Keep functions focused and small

### JavaScript/React (Frontend)
- Use functional components with hooks
- Follow existing component structure
- Use TypeScript where possible
- Keep components reusable

## Plugin Development

See [HUB-IMPLEMENTATION-PLAN.md](./HUB-IMPLEMENTATION-PLAN.md) for plugin architecture details.

### Creating a Built-in Plugin

1. Create plugin file in `backend/app/plugins/builtin/`
2. Extend `PluginBase` class
3. Implement required methods
4. Register in plugin loader
5. Add tests

### Creating an External Plugin

1. Use the Plugin SDK (coming soon)
2. Implement the plugin interface
3. Deploy as standalone service
4. Register with hub via API

## Testing

- Write unit tests for all new functionality
- Ensure existing tests pass
- Add integration tests for plugin interactions

## Documentation

- Update README.md for user-facing changes
- Update HUB-IMPLEMENTATION-PLAN.md for architectural changes
- Add inline code comments for complex logic
- Update API documentation

## Pull Request Process

1. Ensure all tests pass
2. Update documentation
3. Add clear description of changes
4. Reference any related issues
5. Wait for review and address feedback

## Questions?

Open an issue for questions or discussion about:
- Feature ideas
- Bug reports
- Documentation improvements
- Architecture decisions

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.
