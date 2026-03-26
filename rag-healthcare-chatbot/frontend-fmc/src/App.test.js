import { render, screen } from '@testing-library/react';
import App from './App';

jest.mock('react-markdown', () => ({ children }) => children);
jest.mock('remark-gfm', () => () => null);
jest.mock('remark-gemoji', () => () => null);
jest.mock('lottie-web', () => ({
  loadAnimation: () => ({
    destroy: jest.fn(),
  }),
}));

test('renders KinexAssist chat greeting', () => {
  render(<App />);
  expect(screen.getByText(/how can i assist you with clinical data today/i)).toBeInTheDocument();
});
