/**
 * Check if a file path matches a given pattern
 * Supports glob patterns: *, **, ?, and negation with !
 */
export function matchesPattern(filePath: string, pattern: string): boolean {
  // Normalize path separators
  const normalizedPath = filePath.replace(/\\/g, '/');
  let normalizedPattern = pattern.replace(/\\/g, '/');

  // Handle negation
  const isNegated = normalizedPattern.startsWith('!');
  if (isNegated) {
    normalizedPattern = normalizedPattern.slice(1);
  }

  // Convert glob pattern to regex
  const regex = globToRegex(normalizedPattern);
  const matches = regex.test(normalizedPath);

  return isNegated ? !matches : matches;
}

/**
 * Check if a file path matches any of the given patterns
 */
export function matchesAnyPattern(filePath: string, patterns: string[]): boolean {
  return patterns.some(pattern => matchesPattern(filePath, pattern));
}

/**
 * Convert a glob pattern to a regular expression
 * Supports: *, **, ?, character classes [abc], and ranges [a-z]
 */
function globToRegex(pattern: string): RegExp {
  let regexPattern = '';
  let i = 0;

  while (i < pattern.length) {
    const char = pattern[i];

    switch (char) {
      case '*':
        if (pattern[i + 1] === '*') {
          // Handle **
          if (pattern[i + 2] === '/') {
            regexPattern += '(?:.*/)?';
            i += 3;
          } else {
            regexPattern += '.*';
            i += 2;
          }
        } else {
          // Handle single *
          regexPattern += '[^/]*';
          i++;
        }
        break;

      case '?':
        regexPattern += '[^/]';
        i++;
        break;

      case '[': {
        // Handle character classes
        let j = i + 1;
        while (j < pattern.length && pattern[j] !== ']') {
          j++;
        }
        if (j < pattern.length) {
          const charClass = pattern.slice(i, j + 1);
          regexPattern += charClass;
          i = j + 1;
        } else {
          regexPattern += '\\[';
          i++;
        }
        break;
      }

      case '.':
      case '+':
      case '^':
      case '$':
      case '(':
      case ')':
      case '{':
      case '}':
      case '|':
      case '\\':
        // Escape regex special characters
        regexPattern += '\\' + char;
        i++;
        break;

      default:
        regexPattern += char;
        i++;
        break;
    }
  }

  return new RegExp('^' + regexPattern + '$');
}
