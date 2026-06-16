const fallbackChapters = ['Introduction', 'Core Concepts', 'Practice and Revision'];

export async function extractChaptersFromTextbook({ title, subject }) {
  if (title?.toLowerCase().includes('science')) {
    return ['Nutrition in Plants', 'Heat', 'Acids Bases and Salts'];
  }
  if (title?.toLowerCase().includes('math') || subject === 'Mathematics') {
    return ['Integers', 'Fractions and Decimals', 'Simple Equations'];
  }
  return fallbackChapters;
}

export async function generateLesson({ classLevel, subject, chapter, iqLevel, disabilities = [] }) {
  const simple = iqLevel === 'basic';
  const advanced = iqLevel === 'advanced';
  return {
    content_text: `${chapter} is an important topic in Class ${classLevel} ${subject}. ${simple ? 'We will learn it step by step with simple words.' : advanced ? 'This lesson connects the concept to deeper reasoning and real-world applications.' : 'This lesson explains the topic clearly with examples.'}\n\nFirst, understand the main idea. Then look at examples. Finally, try to explain it in your own words. This helps your brain remember the lesson better. ${disabilities.includes('visual') ? 'Audio and descriptive text are included for visual support.' : ''} ${disabilities.includes('hearing') ? 'Captions and written narration are included for hearing support.' : ''}`,
    key_points: [
      `${chapter} has a main idea you should remember.`,
      'Examples make the concept easier to understand.',
      'Practice helps you check your understanding.',
      'Ask your teacher when a step feels confusing.',
      'Review the key words after the lesson.',
    ],
    visual_description: `Imagine a clear classroom board showing the topic "${chapter}" in the center, with arrows connecting examples and key facts around it.`,
    caption_text: `Today we are learning ${chapter} in ${subject}. Read each idea slowly, pause, and try the examples.`,
    vocabulary: [
      { word: 'Concept', definition: 'A main idea or topic.' },
      { word: 'Example', definition: 'Something that shows how an idea works.' },
      { word: 'Practice', definition: 'Trying again to improve understanding.' },
      { word: 'Review', definition: 'Reading or checking something again.' },
      { word: 'Progress', definition: 'Improvement over time.' },
    ],
    animation_type: pickAnimationType(`${subject} ${chapter}`),
    animation_script: [
      {
        title: 'Start with the main idea',
        caption: `Today we learn the main idea of ${chapter}.`,
        visual: 'A central topic card appears with three connected idea bubbles.',
        narration: `Today we learn the main idea of ${chapter}.`,
      },
      {
        title: 'See an example',
        caption: 'An example makes the idea easier to understand.',
        visual: 'A simple example card slides in next to the topic card.',
        narration: 'Now we look at an example to make the idea easier.',
      },
      {
        title: 'Practice and remember',
        caption: 'Practice helps you remember the lesson.',
        visual: 'A check mark appears after a short practice question.',
        narration: 'Finally, we practice so the idea stays in your memory.',
      },
    ],
  };
}

function pickAnimationType(text) {
  const lower = text.toLowerCase();
  if (lower.includes('ionic') || lower.includes('bond') || lower.includes('electron')) return 'ionic_bond';
  if (lower.includes('photosynthesis')) return 'photosynthesis';
  if (lower.includes('food chain') || lower.includes('ecosystem')) return 'food_chain';
  if (lower.includes('water cycle') || lower.includes('evaporation')) return 'water_cycle';
  if (lower.includes('states of matter') || lower.includes('solid') || lower.includes('liquid') || lower.includes('gas')) return 'states_of_matter';
  if (lower.includes('circuit') || lower.includes('electric')) return 'electric_circuit';
  if (lower.includes('fraction')) return 'fractions';
  if (lower.includes('plant')) return 'plant_parts';
  if (lower.includes('digestion') || lower.includes('digestive')) return 'digestion';
  return 'default_concept';
}

export async function generateAssessment({ classLevel, subject, chapter, assessmentType, iqLevel }) {
  const seed = Date.now().toString(36).slice(-4);
  const topic = chapter || 'this lesson';
  const puzzleTemplates = [
    {
      question: `Mystery clue ${seed}: I am the main idea hiding inside ${topic}. Which answer fits me?`,
      question_type: 'clue_match',
      options: [`Main idea of ${topic}`, 'A random word', 'Only the page number', 'An unrelated story'],
      correct_answer: `Main idea of ${topic}`,
      hint: 'Look for the choice connected to the lesson topic.',
    },
    {
      question: `Odd one out ${seed}: Which option does NOT help you learn ${topic}?`,
      question_type: 'odd_one_out',
      options: ['Looking at examples', 'Reading key points', 'Guessing without reading', 'Asking your teacher'],
      correct_answer: 'Guessing without reading',
      hint: 'Find the choice that is not a learning strategy.',
    },
    {
      question: `Sequence puzzle ${seed}: What is the best first step for ${topic}?`,
      question_type: 'sequence',
      options: ['Read the main idea', 'Look at examples', 'Try practice', 'Review feedback'],
      correct_answer: 'Read the main idea → Look at examples → Try practice → Review feedback',
      hint: 'Build the best learning order.',
    },
    {
      question: `Match the clue ${seed}: Which activity checks your understanding?`,
      question_type: 'clue_match',
      options: ['Trying a quiz', 'Closing the lesson', 'Deleting notes', 'Avoiding practice'],
      correct_answer: 'Trying a quiz',
      hint: 'Choose the activity that tests what you learned.',
    },
    {
      question: `Fill the blank ${seed}: ______ helps your brain remember ${topic}.`,
      question_type: 'fill_blank',
      options: ['Practice', 'Confusion', 'Noise', 'A blank answer'],
      correct_answer: 'Practice',
      hint: 'Doing something again helps memory.',
    },
  ];
  const quizTemplates = puzzleTemplates.map((item, index) => ({
    ...item,
    question: `Question ${index + 1} ${seed}: ${item.question.replace(/^.*?:\s*/, '')}`,
  }));
  const flashcards = [
    {
      question: `Flashcard ${seed}: What is one key idea from ${topic}?`,
      options: [`A key idea from ${topic}`, 'Unrelated fact', 'Wrong answer', 'Random word'],
      correct_answer: `A key idea from ${topic}`,
    },
    ...quizTemplates,
    {
      question: `Flashcard ${seed}: Why should you review ${topic}?`,
      options: ['To remember better', 'To forget faster', 'To skip learning', 'To avoid practice'],
      correct_answer: 'To remember better',
    },
    {
      question: `Flashcard ${seed}: What helps if ${topic} feels hard?`,
      options: ['Ask for help', 'Stop learning', 'Guess always', 'Ignore examples'],
      correct_answer: 'Ask for help',
    },
  ];
  const questions = assessmentType === 'flashcard' ? flashcards.slice(0, 8) : assessmentType === 'puzzle' ? puzzleTemplates : quizTemplates;
  return { questions };
}

export async function generateFeedback({ assessment, score, totalQuestions, percentage }) {
  return `You scored ${score}/${totalQuestions} (${percentage}%) in ${assessment.subject}. You are building understanding of ${assessment.chapter}. Review the questions you missed, then try one more short practice session.`;
}
